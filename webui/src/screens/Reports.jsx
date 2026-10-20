import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Bars, Columns, Histogram, Lines, StackedBars } from '../components/charts'
import { Button, Empty, Loading, PageHead, Select, Table, Tabs } from '../components/ui'
import { api, useApi } from '../lib/api'
import { fmt } from '../lib/format'

const TABS = ['Outcomes', 'Engagement', 'Scores', 'Enrollments', 'Grade changes']

function ExportButton({ name, rows }) {
  return (
    <Button kind="secondary" size="sm" icon={Download} disabled={!rows?.length}
      onClick={async () => { try { const p = await api('export_csv', { name, rows }); toast.success(`Saved ${p.split(/[\\/]/).pop()} to the exports folder`) } catch (e) { toast.error(e.message) } }}>
      Save as CSV
    </Button>
  )
}

function Card({ title, sub, actions, children }) {
  return (
    <section className="card card-pad">
      <div className="card-head">
        <div><h2 className="card-title">{title}</h2>{sub && <p className="card-sub">{sub}</p>}</div>
        {actions}
      </div>
      {children}
    </section>
  )
}

function Outcomes() {
  const [field, setField] = useState('highest_education')
  const { data } = useApi('report', { kind: 'outcomes', field }, [field])
  if (!data) return <Loading height={400} />
  const best = [...data.rows].sort((a, b) => b.passed - a.passed)[0]
  const worst = [...data.rows].sort((a, b) => a.passed - b.passed)[0]
  return (
    <div className="stack" style={{ gap: 20 }}>
      <Card title="Results by student background" sub="Past courses, 2013–14."
        actions={<div className="row"><Select label="Group by" value={field} onChange={setField} options={Object.entries(data.groups).map(([v, l]) => ({ value: v, label: l }))} width={300} /><ExportButton name="outcomes_by_background" rows={data.rows} /></div>}>
        <StackedBars labelWidth={230} rows={data.rows.map((r) => ({ label: String(r.grp), parts: { Pass: r.passed, Fail: r.failed, Withdrawn: r.withdrawn } }))} />
        <p className="small muted" style={{ marginTop: 14 }}>Highest pass rate: {best.grp} ({best.passed}%, {fmt(best.n)} enrollments). Lowest: {worst.grp} ({worst.passed}%, {fmt(worst.n)}).</p>
      </Card>
      <Card title="Every course" actions={<ExportButton name="course_outcomes" rows={data.courses} />}>
        <Table rowKey="course_id" rows={data.courses} maxHeight={460} columns={[
          { key: 'code', label: 'Code' }, { key: 'title', label: 'Title' },
          { key: 'enrolled', label: 'Enrolled', align: 'r', render: (r) => fmt(r.enrolled) },
          { key: 'completed', label: 'Completed', align: 'r', render: (r) => fmt(r.completed) },
          { key: 'failed', label: 'Failed', align: 'r', render: (r) => fmt(r.failed) },
          { key: 'withdrawn', label: 'Withdrawn', align: 'r', render: (r) => fmt(r.withdrawn) },
          { key: 'completion_rate', label: 'Completion', align: 'r', render: (r) => (r.completion_rate === null ? '—' : `${fmt(r.completion_rate, 1)}%`) },
        ]} />
      </Card>
    </div>
  )
}

function CoursePicker({ value, onChange, filter }) {
  const { data } = useApi('courses_search', {}, [])
  const options = (data || []).filter(filter)
  useEffect(() => { if (!value && options.length) onChange(String(options.find((c) => c.code === 'DDD-2013J')?.id || options[0].id)) }, [options.length]) // eslint-disable-line
  return <Select label="Course" value={value} onChange={onChange} options={options.map((c) => ({ value: c.id, label: `${c.code}  ${c.title}` }))} width={360} />
}

function Engagement() {
  const [course, setCourse] = useState('')
  const { data } = useApi(course ? 'report' : null, { kind: 'engagement', course_id: Number(course) }, [course])
  const weeks = data ? [...new Set(data.weekly.map((r) => r.week))].sort((a, b) => a - b) : []
  const series = {}
  if (data) ['Distinction', 'Pass', 'Fail', 'Withdrawn'].forEach((res) => {
    const m = Object.fromEntries(data.weekly.filter((r) => r.result === res).map((r) => [r.week, r.clicks_per_student]))
    if (Object.keys(m).length) series[res] = weeks.map((w) => m[w] || 0)
  })
  return (
    <div className="stack" style={{ gap: 20 }}>
      <Card title="Weekly activity by final result" sub="Average clicks per student each week."
        actions={<div className="row"><CoursePicker value={course} onChange={setCourse} filter={(c) => c.source === 'oulad'} /><ExportButton name="weekly_activity" rows={data?.weekly} /></div>}>
        {data ? <Lines x={weeks} series={series} xLabel="week of course" yLabel="clicks per student" height={300} /> : <Loading height={300} />}
      </Card>
      {data && (
        <Card title="Active days by result" sub="All past courses.">
          <Bars data={data.by_result.map((a) => ({ label: a.result, value: a.avg_active_days, digits: 1 }))} unit=" days" />
        </Card>
      )}
    </div>
  )
}

function Scores() {
  const [course, setCourse] = useState('')
  const { data } = useApi(course ? 'report' : null, { kind: 'scores', course_id: Number(course) }, [course])
  const sorted = data ? [...data.scores].sort((a, b) => a - b) : []
  const above = data ? data.scores.filter((v) => v >= data.pass_mark).length : 0
  return (
    <Card title="Score distribution" sub="Weighted course score of every enrollment with results."
      actions={<div className="row"><CoursePicker value={course} onChange={setCourse} filter={(c) => c.enrolled && c.source !== 'assistments'} /><ExportButton name="scores" rows={data?.scores.map((s) => ({ score: s }))} /></div>}>
      {!data ? <Loading height={260} /> : data.scores.length === 0 ? <Empty title="No scores yet" /> : (
        <>
          <Histogram values={data.scores} mark={data.pass_mark} markLabel={`Pass mark ${data.pass_mark}%`} xLabel="score (%)" height={280} />
          <p className="small muted" style={{ marginTop: 10 }}>{fmt(data.scores.length)} enrollments · median {fmt(sorted[Math.floor(sorted.length / 2)])}% · {fmt((100 * above) / data.scores.length)}% at or above the pass mark</p>
        </>
      )}
    </Card>
  )
}

function Trend() {
  const { data } = useApi('report', { kind: 'trend' }, [])
  return (
    <Card title="New enrollments per month" sub="Registrations peak before each February and October start." actions={<ExportButton name="monthly_enrollments" rows={data} />}>
      {data ? <Columns data={data.slice(-40).map((d) => ({ label: d.month, value: d.enrollments }))} height={300} /> : <Loading height={300} />}
    </Card>
  )
}

function Audit() {
  const { data } = useApi('report', { kind: 'audit' }, [])
  return (
    <Card title="Grade changes" sub="Every score change and who made it."
      actions={<ExportButton name="grade_changes" rows={data} />}>
      {data ? (
        <Table rowKey="changed_at" rows={data} maxHeight={520}
          empty={<Empty title="No score has changed yet">Retake a quiz with a better score and a row appears here.</Empty>}
          columns={[
            { key: 'changed_at', label: 'When' }, { key: 'student', label: 'Student' }, { key: 'course', label: 'Course' },
            { key: 'module', label: 'Module' }, { key: 'old_score', label: 'Old', align: 'r' }, { key: 'new_score', label: 'New', align: 'r' },
            { key: 'changed_by', label: 'By' },
          ]} />
      ) : <Loading height={300} />}
    </Card>
  )
}

export default function Reports() {
  const [tab, setTab] = useState(TABS[0])
  return (
    <>
      <PageHead title="Reports" />
      <div style={{ marginBottom: 18 }}><Tabs id="reports" value={tab} onChange={setTab} items={TABS} /></div>
      {tab === 'Outcomes' && <Outcomes />}
      {tab === 'Engagement' && <Engagement />}
      {tab === 'Scores' && <Scores />}
      {tab === 'Enrollments' && <Trend />}
      {tab === 'Grade changes' && <Audit />}
    </>
  )
}
