import { useEffect, useState } from 'react'
import { ArrowRight, Calendar, Users } from 'lucide-react'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageShell } from '../components/PageShell'
import { TripDetail } from './TripDetail'
import { travelRepository } from '../repositories/travelRepository'
import type { TravelTeam } from '../mock/seed/travelSeed'

type LoadState = 'loading' | 'ready' | 'empty' | 'error'

interface TripsProps {
  tripId?: string | null
  onOpenTrip?: (tripId: string) => void
  onBackToList?: () => void
}

function statusBadgeVariant(status: TravelTeam['status']): 'success' | 'info' | 'default' {
  if (status === 'in_progress') return 'success'
  if (status === 'planned') return 'info'
  return 'default'
}

const statusText: Record<TravelTeam['status'], string> = {
  planned: '计划中',
  in_progress: '进行中',
  completed: '已完成',
}

export function Trips({ tripId = null, onOpenTrip, onBackToList }: TripsProps) {
  const [teams, setTeams] = useState<TravelTeam[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')

  useEffect(() => {
    let mounted = true
    travelRepository.getTeams()
      .then((rows) => {
        if (!mounted) return
        setTeams(rows)
        setLoadState(rows.length > 0 ? 'ready' : 'empty')
      })
      .catch(() => mounted && setLoadState('error'))
    return () => {
      mounted = false
    }
  }, [])

  const handleOpenTrip = (teamId: string) => {
    if (onOpenTrip) return onOpenTrip(teamId)
    window.history.pushState({}, '', `/trips/${encodeURIComponent(teamId)}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  if (tripId) {
    return <TripDetail tripId={tripId} onBack={() => onBackToList?.()} />
  }

  return (
    <PageShell eyebrow="Trips" title="行程管理" description="已切换为真实后端数据源，请先执行部署前 seed 脚本导入演示数据。">
      {loadState === 'loading' ? <p className="rounded-lg bg-slate-100 p-3 text-sm">正在加载旅行团...</p> : null}
      {loadState === 'error' ? <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">加载失败，请检查后端服务与登录状态。</p> : null}
      {loadState === 'empty' ? <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-700">暂无旅行团，请先运行 scripts/seed_travel_demo_data.py</p> : null}
      {loadState === 'ready' ? (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {teams.map((team) => (
            <Card key={team.id} className="cursor-pointer" onClick={() => handleOpenTrip(team.id)}>
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{team.name}</h3>
                  <p className="font-mono text-xs text-slate-500">{team.teamCode}</p>
                </div>
                <Badge variant={statusBadgeVariant(team.status)}>{statusText[team.status]}</Badge>
              </div>
              <div className="space-y-2 text-sm text-slate-600">
                <p className="flex items-center gap-2"><Calendar className="h-4 w-4" />{team.startDate} ~ {team.endDate}</p>
                <p className="flex items-center gap-2"><Users className="h-4 w-4" />{team.guestCount} 位游客</p>
                <p>数据完整度：{team.dataCompleteness}%</p>
                <p>已导入行程：{team.importedSchedule ? '是' : '否'} · 已导入游客：{team.importedGuests ? '是' : '否'}</p>
                <p>今日待办数：{team.todayTodoCount} · 下一通知节点：{team.nextNotificationAt}</p>
              </div>
              <div className="mt-4 flex items-center gap-2 border-t border-slate-200 pt-4" onClick={(event) => event.stopPropagation()}>
                <Button size="sm" className="flex-1" onClick={() => handleOpenTrip(team.id)}>进入团详情 <ArrowRight className="ml-1 inline h-4 w-4" /></Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </PageShell>
  )
}
