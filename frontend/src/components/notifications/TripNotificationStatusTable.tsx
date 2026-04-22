import { Badge } from '../Badge'
import { Card } from '../Card'
import { type TripNotificationSnapshot } from '../../features/notifications/tripNotificationClient'

interface TripNotificationStatusTableProps {
  snapshot: TripNotificationSnapshot | null
}

function channelLabel(code: string): string {
  if (code === 'wechat_work_group') {
    return '企业微信'
  }
  if (code === 'email') {
    return '邮件'
  }
  return '短信'
}

export function TripNotificationStatusTable({ snapshot }: TripNotificationStatusTableProps) {
  return (
    <Card title="发送状态总览" className="border-blue-100">
      {!snapshot ? (
        <p className="text-sm text-slate-500">暂无发送状态数据</p>
      ) : (
        <>
          <div className="mb-4 grid gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-green-100 bg-green-50 p-3">
              <p className="text-xs text-green-700">已发送</p>
              <p className="mt-1 text-xl font-bold text-green-800">{snapshot.sentCount}</p>
            </div>
            <div className="rounded-lg border border-yellow-100 bg-yellow-50 p-3">
              <p className="text-xs text-yellow-700">待发送</p>
              <p className="mt-1 text-xl font-bold text-yellow-800">{snapshot.pendingCount}</p>
            </div>
            <div className="rounded-lg border border-red-100 bg-red-50 p-3">
              <p className="text-xs text-red-700">失败</p>
              <p className="mt-1 text-xl font-bold text-red-800">{snapshot.failedCount}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-700">人工接管</p>
              <p className="mt-1 text-xl font-bold text-slate-900">{snapshot.manualCount}</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="bg-slate-50 text-left text-slate-700">
                  <th className="px-3 py-2 font-semibold">渠道</th>
                  <th className="px-3 py-2 font-semibold">已发送</th>
                  <th className="px-3 py-2 font-semibold">待发送</th>
                  <th className="px-3 py-2 font-semibold">失败</th>
                  <th className="px-3 py-2 font-semibold">人工接管</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.channelBreakdown.map((row) => (
                  <tr key={row.channel} className="border-b border-slate-100">
                    <td className="px-3 py-2">
                      <Badge variant="info">{channelLabel(row.channel)}</Badge>
                    </td>
                    <td className="px-3 py-2">{row.sent}</td>
                    <td className="px-3 py-2">{row.pending}</td>
                    <td className="px-3 py-2">{row.failed}</td>
                    <td className="px-3 py-2">{row.manual}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  )
}
