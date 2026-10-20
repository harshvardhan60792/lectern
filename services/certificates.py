"""Certificates: eligibility, tamper-evident fingerprint, PDF, verification.

The fingerprint is a SHA-256 hash of the facts printed on the certificate.
If anyone edits the student, course, date or score on a PDF, the hash of the
edited facts no longer matches the one stored when it was issued.
"""
import hashlib
import io
from datetime import date
from pathlib import Path

from db import transaction
from services.errors import ValidationError

# Mixed into every fingerprint so a hash can't be recomputed without the app.
_PEPPER = "lectern-certificate-v1"


def certificate_code(student_id: int, course_id: int) -> str:
    digest = hashlib.sha1(f"{student_id}:{course_id}".encode()).hexdigest().upper()
    return f"LEC-{digest[:4]}-{digest[4:8]}"


def fingerprint(code: str, student_name: str, course_title: str, issued_on: str, score: float | None) -> str:
    score_text = "" if score is None else f"{score:.1f}"
    facts = "|".join([_PEPPER, code, student_name, course_title, issued_on, score_text])
    return hashlib.sha256(facts.encode("utf-8")).hexdigest()


def course_score(conn, student_id: int, course_id: int) -> float | None:
    row = conn.execute(
        """SELECT ROUND(COALESCE(SUM(mp.best_score * m.weight) / NULLIF(SUM(m.weight), 0),
                                 AVG(mp.best_score)), 1) AS score
           FROM modules m
           JOIN module_progress mp ON mp.module_id = m.id AND mp.student_id = ?
           WHERE m.course_id = ?""",
        (student_id, course_id),
    ).fetchone()
    return row["score"]


def issue(conn, student_id: int, course_id: int, issued_on: str | None = None, grade: str | None = None) -> dict:
    """Issue a certificate for a completed enrollment. Returns the certificate row."""
    existing = conn.execute(
        "SELECT * FROM certificates WHERE student_id = ? AND course_id = ?", (student_id, course_id)
    ).fetchone()
    if existing:
        return dict(existing)

    info = conn.execute(
        """SELECT s.display_name, c.title FROM students s, courses c
           WHERE s.id = ? AND c.id = ?""",
        (student_id, course_id),
    ).fetchone()
    if info is None:
        raise ValueError("Unknown student or course.")

    issued_on = issued_on or date.today().isoformat()
    score = course_score(conn, student_id, course_id)
    code = certificate_code(student_id, course_id)
    fp = fingerprint(code, info["display_name"], info["title"], issued_on, score)
    conn.execute(
        """INSERT INTO certificates (code, student_id, course_id, issued_on, score, grade, fingerprint)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (code, student_id, course_id, issued_on, score, grade, fp),
    )
    return dict(conn.execute("SELECT * FROM certificates WHERE code = ?", (code,)).fetchone())


def details(conn, code: str) -> dict | None:
    row = conn.execute(
        """SELECT ct.*, s.display_name AS student_name, c.title AS course_title, c.code AS course_code,
                  c.attribution
           FROM certificates ct
           JOIN students s ON s.id = ct.student_id
           JOIN courses c  ON c.id = ct.course_id
           WHERE ct.code = ?""",
        (code.strip().upper(),),
    ).fetchone()
    return dict(row) if row else None


def verify(conn, code: str, student_name: str | None = None, course_title: str | None = None,
           issued_on: str | None = None, score: float | None = None) -> dict:
    """Check a certificate.

    With only a code, confirms it exists and that the stored record still matches
    its fingerprint (catches edits made directly in the database). When the facts
    printed on a PDF are passed in too, they must reproduce the same fingerprint.
    """
    cert = details(conn, code)
    if cert is None:
        return {"valid": False, "reason": "No certificate has this code."}
    if cert["revoked"]:
        return {"valid": False, "reason": "This certificate was revoked.", "certificate": cert}

    stored = fingerprint(cert["code"], cert["student_name"], cert["course_title"], cert["issued_on"], cert["score"])
    if stored != cert["fingerprint"]:
        return {"valid": False, "reason": "The record was changed after the certificate was issued.",
                "certificate": cert}

    claimed = {
        "student_name": student_name, "course_title": course_title,
        "issued_on": issued_on, "score": score,
    }
    if any(v is not None for v in claimed.values()):
        recomputed = fingerprint(
            cert["code"],
            student_name if student_name is not None else cert["student_name"],
            course_title if course_title is not None else cert["course_title"],
            issued_on if issued_on is not None else cert["issued_on"],
            score if score is not None else cert["score"],
        )
        if recomputed != cert["fingerprint"]:
            return {"valid": False, "reason": "The details shown do not match what was issued.",
                    "certificate": cert}

    return {"valid": True, "reason": "Genuine certificate.", "certificate": cert}


def revoke(conn, code: str) -> None:
    with transaction(conn):
        cur = conn.execute("UPDATE certificates SET revoked = 1 WHERE code = ?", (code.strip().upper(),))
    if cur.rowcount == 0:
        raise ValidationError("No certificate has this code.")


def search(conn, text: str = "", limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    where, params = "", []
    if text.strip():
        where = "WHERE ct.code LIKE ? OR s.display_name LIKE ? OR c.code LIKE ?"
        params = [f"%{text.strip()}%"] * 3
    base = f"""FROM certificates ct JOIN students s ON s.id = ct.student_id JOIN courses c ON c.id = ct.course_id
               {where}"""
    total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT ct.code, s.display_name AS student, c.code AS course_code, c.title AS course_title,
                   ct.issued_on, ct.score, ct.grade, ct.revoked
            {base} ORDER BY ct.issued_on DESC, ct.id DESC LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def list_for_student(conn, student_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT ct.code, ct.issued_on, ct.score, ct.grade, ct.revoked, c.title AS course_title
           FROM certificates ct JOIN courses c ON c.id = ct.course_id
           WHERE ct.student_id = ? ORDER BY ct.issued_on DESC""",
        (student_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def render_pdf(conn, code: str, out_path: Path) -> Path:
    """Draw the certificate as an A4 landscape PDF with a QR code for verification."""
    import qrcode
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    cert = details(conn, code)
    if cert is None:
        raise ValueError("No certificate has this code.")

    ink, accent, paper, muted = HexColor("#1F1B16"), HexColor("#7A2E2A"), HexColor("#F7F3EA"), HexColor("#6B6358")
    width, height = landscape(A4)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(out_path), pagesize=(width, height))
    pdf.setTitle(f"Certificate {cert['code']}")

    pdf.setFillColor(paper)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setStrokeColor(ink)
    pdf.setLineWidth(1.2)
    pdf.rect(28, 28, width - 56, height - 56)
    pdf.setLineWidth(0.4)
    pdf.rect(34, 34, width - 68, height - 68)

    pdf.setFillColor(accent)
    pdf.setFont("Times-Bold", 14)
    pdf.drawString(70, height - 90, "LECTERN")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(70, height - 104, "Certificate of completion")

    pdf.setFillColor(ink)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(70, height - 190, "This certifies that")
    pdf.setFont("Times-Bold", 40)
    pdf.drawString(70, height - 238, cert["student_name"])
    pdf.setFont("Helvetica", 12)
    pdf.drawString(70, height - 276, "has completed")
    pdf.setFont("Times-Roman", 24)
    pdf.drawString(70, height - 310, cert["course_title"])

    pdf.setFont("Helvetica", 11)
    lines = [f"Issued {cert['issued_on']}"]
    if cert["score"] is not None:
        lines.append(f"Final score {cert['score']:.1f}%")
    if cert["grade"]:
        lines.append(f"Result: {cert['grade']}")
    pdf.drawString(70, height - 350, "   ·   ".join(lines))

    payload = f"LECTERN:{cert['code']}:{cert['fingerprint'][:16]}"
    qr = qrcode.QRCode(border=1, box_size=6)
    qr.add_data(payload)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="#1F1B16", back_color="#F7F3EA").save(buf, format="PNG")
    buf.seek(0)
    pdf.drawImage(ImageReader(buf), width - 200, 70, 120, 120)

    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(70, 92, f"Certificate code  {cert['code']}")
    pdf.drawString(70, 80, f"Fingerprint  {cert['fingerprint'][:32]}")
    pdf.drawString(70, 68, f"             {cert['fingerprint'][32:]}")
    pdf.drawString(width - 200, 58, "Scan or enter the code in Lectern to verify")
    if cert.get("attribution"):
        pdf.drawString(70, 50, cert["attribution"][:140])

    pdf.showPage()
    pdf.save()
    return out_path
