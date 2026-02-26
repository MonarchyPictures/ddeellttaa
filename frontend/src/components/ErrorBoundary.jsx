import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-900 text-white p-8 flex flex-col items-center justify-center">
          <h1 className="text-3xl font-bold text-red-500 mb-4">Something went wrong</h1>
          <div className="bg-black/50 p-6 rounded-xl border border-red-500/20 max-w-2xl w-full overflow-auto">
            <h2 className="text-xl font-semibold mb-2">{this.state.error?.toString()}</h2>
            <pre className="text-xs text-gray-400 whitespace-pre-wrap">
              {this.state.errorInfo?.componentStack}
            </pre>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
