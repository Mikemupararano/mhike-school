export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-6 text-center">
      <h1 className="text-4xl font-extrabold text-slate-900 sm:text-5xl">
        Mhike School
      </h1>

      <p className="mt-4 text-lg text-slate-600">
        Welcome to the platform.
      </p>

      <div className="mt-8 flex gap-4">
        <a
          href="/login"
          className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
        >
          Login
        </a>

        <a
          href="/dashboard"
          className="rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          Dashboard
        </a>
      </div>
    </main>
  );
}