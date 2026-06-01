const rows = [
  { name: '早安问候', sent: 12, pending: 0 },
  { name: '午间提醒', sent: 0, pending: 12 },
  { name: '晚安问候', sent: 12, pending: 0 },
]

export function TripNotificationStatusTable() {
  return (
    <div className="mt-6 rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3 font-semibold text-gray-900">发送状态总览</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="px-4 py-3 text-left font-medium text-gray-700">通知规则</th>
            <th className="px-4 py-3 text-right font-medium text-gray-700">已发送</th>
            <th className="px-4 py-3 text-right font-medium text-gray-700">待发送</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {rows.map((row) => (
            <tr key={row.name}>
              <td className="px-4 py-3 text-gray-900">{row.name}</td>
              <td className="px-4 py-3 text-right text-green-700">{row.sent}</td>
              <td className="px-4 py-3 text-right text-yellow-700">{row.pending}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
