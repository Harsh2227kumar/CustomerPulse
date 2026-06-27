/**
 * Auth group layout — full-height, centered, no sidebar or topbar.
 * Wraps /login and any future standalone auth pages.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {children}
    </div>
  );
}
