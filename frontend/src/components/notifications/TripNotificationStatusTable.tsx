const rows = [
  { name: '早安问候', sent: 12, pending: 0 },
  { name: '午间提醒', sent: 0, pending: 12 },
  { name: '晚安问候', sent: 12, pending: 0 },
]

export function TripNotificationStatusTable() {
  return (
    <div className="mt-6 rounded-control border border-paper-200 bg-white">
      <div className="border-b border-paper-200 bg-paper-50 px-4 py-3 font-semibold text-paper-900">发送状态总览</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-paper-200">
            <th className="px-4 py-3 text-left font-medium text-paper-700">通知规则</th>
            <th className="px-4 py-3 text-right font-medium text-paper-700">已发送</th>
            <th className="px-4 py-3 text-right font-medium text-paper-700">待发送</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-paper-200">
          {rows.map((row) => (
            <tr key={row.name}>
              <td className="px-4 py-3 text-paper-900">{row.name}</td>
              <td className="px-4 py-3 text-right text-success-700">{row.sent}</td>
              <td className="px-4 py-3 text-right text-warning-700">{row.pending}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
