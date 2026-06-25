import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Create Account</h1>
          <p className="text-gray-400 text-sm">Start generating publication-ready research papers</p>
        </div>
        <SignUp
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "bg-gray-900 border border-gray-800 shadow-2xl rounded-xl",
              headerTitle: "text-white",
              headerSubtitle: "text-gray-400",
              formFieldInput: "bg-gray-800 border-gray-700 text-white focus:border-blue-500",
              formButtonPrimary: "bg-blue-600 hover:bg-blue-500",
              footerActionLink: "text-blue-400",
            },
          }}
          afterSignUpUrl="/dashboard"
          redirectUrl="/dashboard"
        />
      </div>
    </div>
  );
}
