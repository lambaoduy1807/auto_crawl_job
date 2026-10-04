import { useState, useMemo, useEffect } from 'react'
import { fetchJobMatches, markJobApplied, markJobNotApplied } from './api'

type MatchLevel = 'HIGH' | 'MEDIUM' | 'LOW' | string
type WorkModel = 'Remote' | 'Hybrid' | 'On-site' | string
type ExperienceLevel = 'Intern' | 'Fresher' | 'Junior' | 'Senior' | string

interface Job {
  id: number | string
  recordId: string
  jobId: string
  title: string
  company: string
  salary: string
  location: string
  workModel: WorkModel
  experience: ExperienceLevel
  cv: string
  source: string
  matchScore: number
  matchLevel: MatchLevel
  matchedSkills: string[]
  missingSkills: string[]
  jobUrl: string
  description: string
  requirements: string
  benefits: string
  aiExplanation: string
  allMatchedSkills: string[]
  allMissingSkills: string[]
  experienceMatch: boolean | null
  educationMatch: boolean | null
  languageMatch: boolean | null
  positionMatch: boolean | null
  createdAt: string
  updatedAt: string
  isApplied: boolean | null
}

// Removed mock data

const matchColor = {
  HIGH: { badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200', dot: 'bg-emerald-500', score: 'text-emerald-700' },
  MEDIUM: { badge: 'bg-amber-50 text-amber-700 border border-amber-200', dot: 'bg-amber-500', score: 'text-amber-700' },
  LOW: { badge: 'bg-red-50 text-red-700 border border-red-200', dot: 'bg-red-500', score: 'text-red-700' },
}

const expColor: Record<string, string> = {
  Intern: 'bg-purple-50 text-purple-700 border border-purple-200',
  Fresher: 'bg-blue-50 text-blue-700 border border-blue-200',
  Junior: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
  Senior: 'bg-orange-50 text-orange-700 border border-orange-200',
}

function MatchBadge({ level }: { level: MatchLevel }) {
  const c = matchColor[level as keyof typeof matchColor] || { badge: 'bg-gray-50 text-gray-700 border border-gray-200', dot: 'bg-gray-500', score: 'text-gray-700' }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${c.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {level}
    </span>
  )
}

function SkillTag({ label, variant }: { label: string; variant: 'match' | 'miss' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
      variant === 'match'
        ? 'bg-indigo-50 text-indigo-700 border border-indigo-100'
        : 'bg-rose-50 text-rose-700 border border-rose-100'
    } max-w-40 min-w-0 truncate`} title={label}>
      {label}
    </span>
  )
}

function ScoreBar({ score, level }: { score: number; level: MatchLevel }) {
  const color = level === 'HIGH' ? 'bg-emerald-500' : level === 'MEDIUM' ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="mt-1.5 h-1.5 w-full rounded-full bg-gray-100 overflow-hidden">
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${score}%` }} />
    </div>
  )
}

function parseSkillList(value: string | null) {
  const wrapped = (value ?? '').trim().replace(/^\{([\s\S]*)\}$/, '$1').replace(/^\[([\s\S]*)\]$/, '$1')
  if (!wrapped) return []

  return wrapped
    .split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)/)
    .map(skill => skill.trim().replace(/^"(.*)"$/, '$1'))
    .filter(Boolean)
}

function ExpandedRow({ job }: { job: Job }) {
  return (
    <tr>
      <td colSpan={8} className="px-0 py-0">
        <div className="border-t border-indigo-100 bg-gradient-to-b from-indigo-50/60 to-white px-6 py-5">
          <dl className="mb-5">
            <div className="w-fit min-w-32 border-b border-gray-200/80 pb-2">
              <dt className="text-xs font-semibold uppercase text-gray-400">Source</dt>
              <dd className="mt-1 break-words text-sm text-gray-800">{job.source || '—'}</dd>
            </div>
          </dl>

          <div className="grid grid-cols-1 gap-5 2xl:grid-cols-3">
            {/* Left */}
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Job Description</h4>
                <p className="whitespace-pre-wrap break-words text-sm text-gray-700 leading-relaxed">{job.description || '—'}</p>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Benefits</h4>
                <p className="whitespace-pre-wrap break-words text-sm text-gray-700 leading-relaxed">{job.benefits || '—'}</p>
              </div>
            </div>

            {/* Middle */}
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Requirements</h4>
                <p className="whitespace-pre-wrap break-words text-sm text-gray-700 leading-relaxed">{job.requirements || '—'}</p>
              </div>
            </div>

            {/* Right */}
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">AI Match Analysis</h4>
                <div className="rounded-lg border border-indigo-100 bg-white p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.416A4.004 4.004 0 0112 20a4.004 4.004 0 01-2.99-1.342l-.347-.415z" />
                    </svg>
                    <span className="text-xs font-semibold text-indigo-700">Reasoning</span>
                  </div>
                  <p className="whitespace-pre-wrap break-words text-sm text-gray-700 leading-relaxed">{job.aiExplanation || '—'}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">All Matched</h4>
                  <div className="flex flex-wrap gap-1">
                    {job.allMatchedSkills.map(s => <SkillTag key={s} label={s} variant="match" />)}
                  </div>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">All Missing</h4>
                  <div className="flex flex-wrap gap-1">
                    {job.allMissingSkills.map(s => <SkillTag key={s} label={s} variant="miss" />)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </td>
    </tr>
  )
}

export default function App() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [matchFilter, setMatchFilter] = useState<'ALL' | MatchLevel>('ALL')
  const [expFilter, setExpFilter] = useState<'ALL' | ExperienceLevel>('ALL')
  const [modelFilter, setModelFilter] = useState<'ALL' | WorkModel>('ALL')
  const [sortAsc, setSortAsc] = useState(false)
  const [createdFrom, setCreatedFrom] = useState('')
  const [createdTo, setCreatedTo] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [expandedId, setExpandedId] = useState<string | number | null>(null)
  const [tableSearch, setTableSearch] = useState('')
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null)
  const [applyError, setApplyError] = useState('')

  const loadData = () => {
    setLoading(true)
    fetchJobMatches().then(data => {
      const mappedJobs: Job[] = data.map((item, index) => {
        const matchedSkills = parseSkillList(item.matched_skills)
        const missingSkills = parseSkillList(item.missing_skills)
        return {
          id: item.id ?? item.job_id ?? index,
          recordId: String(item.id ?? ''),
          jobId: item.job_id ?? '',
          title: item.title ?? 'Unknown Title',
          company: item.company ?? 'Unknown Company',
          salary: item.salary ?? '',
          location: item.location ?? 'Unknown Location',
          workModel: item.working_model ?? 'Not specified',
          experience: item.experience ?? 'Not specified',
          cv: item.cv_name ?? 'Unknown CV',
          source: item.source ?? '',
          matchScore: Number.parseFloat(item.match_score ?? '') || 0,
          matchLevel: (item.match_level?.toUpperCase() as MatchLevel) || 'LOW',
          matchedSkills,
          missingSkills,
          jobUrl: item.url ?? '',
          description: item.description ?? '',
          requirements: item.requirements ?? '',
          benefits: item.benefits ?? '',
          aiExplanation: item.match_reason ?? '',
          allMatchedSkills: matchedSkills,
          allMissingSkills: missingSkills,
          experienceMatch: item.experience_match,
          educationMatch: item.education_match,
          languageMatch: item.language_match,
          positionMatch: item.position_match,
          createdAt: item.created_at ?? '',
          updatedAt: item.updated_at ?? '',
          isApplied: item.is_applied,
        }
      })
      setJobs(mappedJobs)
    }).catch(err => {
      console.error(err)
    }).finally(() => {
      setLoading(false)
    })
  }

  useEffect(() => {
    loadData()
  }, [])

  const filtered = useMemo(() => {
    let list = [...jobs]
    const q = (search + tableSearch).toLowerCase().trim()
    if (q) list = list.filter(j => j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q))
    if (matchFilter !== 'ALL') list = list.filter(j => j.matchLevel === matchFilter)
    if (expFilter !== 'ALL') list = list.filter(j => j.experience === expFilter)
    if (modelFilter !== 'ALL') list = list.filter(j => j.workModel === modelFilter)
    if (createdFrom) {
      const from = new Date(`${createdFrom}T00:00:00`).getTime()
      list = list.filter(j => {
        const createdAt = Date.parse(j.createdAt)
        return !Number.isNaN(createdAt) && createdAt >= from
      })
    }
    if (createdTo) {
      const to = new Date(`${createdTo}T23:59:59.999`).getTime()
      list = list.filter(j => {
        const createdAt = Date.parse(j.createdAt)
        return !Number.isNaN(createdAt) && createdAt <= to
      })
    }
    const updatedAtTime = (value: string) => {
      const timestamp = Date.parse(value)
      return Number.isNaN(timestamp) ? 0 : timestamp
    }
    list.sort((a, b) =>
      sortAsc
        ? updatedAtTime(a.updatedAt) - updatedAtTime(b.updatedAt)
        : updatedAtTime(b.updatedAt) - updatedAtTime(a.updatedAt),
    )
    return list
  }, [jobs, search, tableSearch, matchFilter, expFilter, modelFilter, sortAsc, createdFrom, createdTo])

  const pageSize = 10
  const pageCount = Math.ceil(filtered.length / pageSize)
  const pageJobs = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  useEffect(() => {
    setCurrentPage(1)
  }, [search, tableSearch, matchFilter, expFilter, modelFilter, createdFrom, createdTo])

  useEffect(() => {
    if (pageCount > 0 && currentPage > pageCount) setCurrentPage(pageCount)
  }, [pageCount, currentPage])

  const stats = useMemo(() => {
    if (jobs.length === 0) return { total: 0, cvs: 0, matched: 0, avgScore: 0 }
    const matched = jobs.filter(j => j.matchLevel === 'HIGH').length
    const avgScore = Math.round(jobs.reduce((s, j) => s + j.matchScore, 0) / jobs.length)
    const cvSet = new Set(jobs.map(j => j.cv))
    return { total: jobs.length, cvs: cvSet.size, matched, avgScore }
  }, [jobs])

  const handleRowClick = (id: string | number) => {
    setExpandedId(prev => prev === id ? null : id)
  }

  const handleAppliedChange = async (job: Job, isApplied: boolean) => {
    if (job.isApplied === isApplied || !job.recordId) return

    setApplyingJobId(job.recordId)
    setApplyError('')
    try {
      if (isApplied) {
        await markJobApplied(job.recordId)
      } else {
        await markJobNotApplied(job.recordId)
      }
      setJobs(current => current.map(currentJob =>
        currentJob.recordId === job.recordId ? { ...currentJob, isApplied } : currentJob,
      ))
    } catch (error) {
      setApplyError(error instanceof Error ? error.message : 'Could not update applied status')
    } finally {
      setApplyingJobId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100" style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="font-semibold text-gray-900 text-sm">CV Matcher</span>
          </div>

          <div className="w-px h-5 bg-gray-200 mx-1" />

          <span className="text-sm font-medium text-gray-500 hidden sm:block">Job Matching Dashboard</span>

          {/* Search */}
          <div className="flex-1 max-w-xs ml-auto relative hidden md:block">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search jobs..."
              className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-gray-200 bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
            />
          </div>

          {/* Refresh */}
          <button onClick={loadData} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-all">
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="hidden sm:inline">{loading ? 'Loading...' : 'Refresh'}</span>
          </button>

          {/* Avatar */}
          <div className="w-7 h-7 rounded-full bg-indigo-100 border-2 border-indigo-200 flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-indigo-700">LD</span>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-6 space-y-5">
        {applyError && <p role="alert" className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{applyError}</p>}
        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              label: 'Total Jobs',
              value: stats.total,
              icon: (
                <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              ),
              bg: 'bg-indigo-50',
              sub: 'Crawled this session',
            },
            {
              label: 'CVs Available',
              value: stats.cvs,
              icon: (
                <svg className="w-4 h-4 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              ),
              bg: 'bg-violet-50',
              sub: 'Unique candidates',
            },
            {
              label: 'High Matches',
              value: stats.matched,
              icon: (
                <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
              ),
              bg: 'bg-emerald-50',
              sub: 'Score ≥ 70%',
            },
            {
              label: 'Avg. Match Score',
              value: `${stats.avgScore}%`,
              icon: (
                <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
              ),
              bg: 'bg-amber-50',
              sub: 'Across all jobs',
            },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-200 px-4 py-3.5 flex items-center gap-3 shadow-sm">
              <div className={`w-9 h-9 rounded-lg ${s.bg} flex items-center justify-center shrink-0`}>
                {s.icon}
              </div>
              <div className="min-w-0">
                <p className="text-xs text-gray-500 truncate">{s.label}</p>
                <p className="text-xl font-bold text-gray-900 leading-tight">{s.value}</p>
                <p className="text-xs text-gray-400">{s.sub}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Table card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Filters bar */}
          <div className="px-5 py-3.5 border-b border-gray-100 flex flex-wrap gap-2 items-center">
            {/* Table search */}
            <div className="relative min-w-[180px] flex-1 max-w-xs">
              <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                value={tableSearch}
                onChange={e => setTableSearch(e.target.value)}
                placeholder="Filter by title or company…"
                className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-gray-200 bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
              />
            </div>

            <div className="flex flex-wrap gap-2 ml-auto items-center">
              {/* Match level */}
              <select
                value={matchFilter}
                onChange={e => setMatchFilter(e.target.value as any)}
                className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 cursor-pointer"
              >
                <option value="ALL">All Levels</option>
                <option value="HIGH">High Match</option>
                <option value="MEDIUM">Medium Match</option>
                <option value="LOW">Low Match</option>
              </select>

              {/* Experience */}
              <select
                value={expFilter}
                onChange={e => setExpFilter(e.target.value as any)}
                className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 cursor-pointer"
              >
                <option value="ALL">All Experience</option>
                <option value="Intern">Intern</option>
                <option value="Fresher">Fresher</option>
                <option value="Junior">Junior</option>
                <option value="Senior">Senior</option>
              </select>

              {/* Work model */}
              <select
                value={modelFilter}
                onChange={e => setModelFilter(e.target.value as any)}
                className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 cursor-pointer"
              >
                <option value="ALL">All Models</option>
                <option value="Remote">Remote</option>
                <option value="Hybrid">Hybrid</option>
                <option value="On-site">On-site</option>
              </select>

              <label className="flex items-center gap-2 text-xs text-gray-500">
                Created from
                <input
                  type="date"
                  value={createdFrom}
                  max={createdTo || undefined}
                  onChange={e => setCreatedFrom(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
                />
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-500">
                Created to
                <input
                  type="date"
                  value={createdTo}
                  min={createdFrom || undefined}
                  onChange={e => setCreatedTo(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
                />
              </label>

              {/* Sort */}
              <button
                onClick={() => setSortAsc(p => !p)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={sortAsc ? "M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" : "M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"} />
                </svg>
                Updated at {sortAsc ? '↑' : '↓'}
              </button>

              <span className="text-xs text-gray-400 font-medium">{filtered.length} jobs</span>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['Job', 'Location', 'Exp.', 'CV', 'Match Score', 'Matched Skills', 'Missing Skills', 'Action'].map(col => (
                    <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-sm text-gray-400">
                      No jobs match the current filters.
                    </td>
                  </tr>
                )}
                {pageJobs.map(job => {
                  const expanded = expandedId === job.id
                  const mc = matchColor[job.matchLevel as keyof typeof matchColor] || { badge: 'bg-gray-50 text-gray-700 border border-gray-200', dot: 'bg-gray-500', score: 'text-gray-700' }
                  return (
                    <>
                      <tr
                        key={job.id}
                        onClick={() => handleRowClick(job.id)}
                        className={`border-b border-gray-100 cursor-pointer transition-colors hover:bg-indigo-50/40 ${expanded ? 'bg-indigo-50/40' : ''}`}
                      >
                        {/* Job */}
                        <td className="px-4 py-3.5 max-w-[220px] min-w-0">
                          <div className="flex items-start gap-2">
                            <div className="w-7 h-7 rounded-md bg-gray-100 border border-gray-200 flex items-center justify-center shrink-0 mt-0.5">
                              <span className="text-xs font-bold text-gray-500">{job.company.charAt(0)}</span>
                            </div>
                            <div className="min-w-0">
                              <p title={job.title} className="font-medium text-gray-900 leading-snug line-clamp-2 break-words text-sm">{job.title}</p>
                              <p title={job.company} className="mt-0.5 max-w-full truncate text-xs text-gray-500">{job.company}</p>
                              {job.isApplied ? (
                                <button
                                  type="button"
                                  onClick={event => {
                                    event.stopPropagation()
                                    void handleAppliedChange(job, false)
                                  }}
                                  disabled={applyingJobId === job.recordId}
                                  className="mt-2 rounded border border-emerald-200 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                                >
                                  {applyingJobId === job.recordId ? 'Saving…' : 'Undo applied'}
                                </button>
                              ) : (
                                <label
                                  onClick={event => event.stopPropagation()}
                                  className="mt-2 inline-flex cursor-pointer items-center gap-1.5 text-xs text-gray-600"
                                >
                                  <input
                                    type="radio"
                                    name={`applied-${job.recordId || job.id}`}
                                    checked={false}
                                    disabled={applyingJobId === job.recordId || !job.recordId}
                                    onChange={() => void handleAppliedChange(job, true)}
                                    className="accent-emerald-600"
                                  />
                                  <span>{applyingJobId === job.recordId ? 'Saving…' : 'Mark applied'}</span>
                                </label>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Location */}
                        <td className="px-4 py-3.5 max-w-[180px] min-w-0">
                          <p title={job.location} className="line-clamp-2 break-words text-sm text-gray-700">{job.location}</p>
                          <span title={job.workModel} className="block max-w-full truncate text-xs text-gray-500">{job.workModel}</span>
                        </td>

                        {/* Experience */}
                        <td className="px-4 py-3.5 max-w-[160px] min-w-0">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${expColor[job.experience] || 'bg-gray-50 text-gray-700 border border-gray-200'}`}>
                            {job.experience}
                          </span>
                        </td>

                        {/* CV */}
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                              <span className="text-xs font-semibold text-indigo-700">{job.cv.split(' ').map(w => w[0]).join('').slice(0, 2)}</span>
                            </div>
                            <span title={job.cv} className="max-w-[120px] truncate text-sm font-medium text-gray-800">{job.cv}</span>
                          </div>
                        </td>

                        {/* Match Score */}
                        <td className="px-4 py-3.5 whitespace-nowrap min-w-[110px]">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-lg font-bold ${mc.score}`}>{job.matchScore}%</span>
                              <MatchBadge level={job.matchLevel} />
                            </div>
                            <ScoreBar score={job.matchScore} level={job.matchLevel} />
                          </div>
                        </td>

                        {/* Matched */}
                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap gap-1">
                            {job.matchedSkills.map(s => <SkillTag key={s} label={s} variant="match" />)}
                          </div>
                        </td>

                        {/* Missing */}
                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap gap-1">
                            {job.missingSkills.map(s => <SkillTag key={s} label={s} variant="miss" />)}
                          </div>
                        </td>

                        {/* Action */}
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <a
                              href={job.jobUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition-colors"
                            >
                              View Job
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                            <svg
                              className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </td>
                      </tr>
                      {expanded && <ExpandedRow key={`exp-${job.id}`} job={job} />}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              Showing {filtered.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, filtered.length)} of {filtered.length} filtered jobs ({jobs.length} total)
            </p>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage(page => Math.max(1, page - 1))}
                  disabled={currentPage <= 1}
                  className="rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="min-w-20 text-center text-xs text-gray-500">
                  Page {pageCount === 0 ? 0 : currentPage} of {pageCount}
                </span>
                <button
                  type="button"
                  onClick={() => setCurrentPage(page => Math.min(pageCount, page + 1))}
                  disabled={currentPage >= pageCount}
                  className="rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="text-xs text-gray-500">AI matching active</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
