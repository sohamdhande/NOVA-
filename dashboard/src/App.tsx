import { AuthProvider, useAuth } from './context/AuthContext'
import { LockScreen } from './components/LockScreen'
import { DashboardLayout } from './layouts/DashboardLayout'
import { ToastContainer } from './components/Toast/ToastContainer'
import { useEventBus } from './hooks/useEventBus'

function BiometricGate() {
  const { isAuthenticated } = useAuth()
  useEventBus()

  if (!isAuthenticated) {
    return <LockScreen />
  }

  return (
    <>
      <DashboardLayout />
      <ToastContainer />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BiometricGate />
    </AuthProvider>
  )
}
