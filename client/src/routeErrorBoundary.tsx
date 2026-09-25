
import { useRouteError, isRouteErrorResponse } from 'react-router-dom'

function RouteErrorBoundary() {
  const err = useRouteError()
  return (
    <div className="m-6 rounded-xl border border-red-500/40 bg-red-950/40 p-6">
      <h2 className="text-red-300 text-xl font-bold">Oops, something went wrong.</h2>
      <pre className="mt-3 text-red-200/80 text-sm">
        {isRouteErrorResponse(err) ? `${err.status} ${err.statusText}` : String(err)}
      </pre>
    </div>
  )
}
export default RouteErrorBoundary;
