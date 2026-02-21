import { redirect } from 'next/navigation';

// Registration is closed during beta — route visitors to the waitlist instead
export default function RegisterPage() {
  redirect('/waitlist');
}
