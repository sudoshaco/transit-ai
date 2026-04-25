import AuthForm from '@/components/auth/AuthForm'

export const metadata = { title: 'Anmelden — TransitAI' }

export default function LoginPage() {
  return <AuthForm mode="login" />
}
