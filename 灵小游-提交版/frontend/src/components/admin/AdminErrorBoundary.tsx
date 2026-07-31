import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class AdminErrorBoundary extends Component<Props, State> {
  override state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[AdminErrorBoundary] 页面渲染崩溃:', error.message, info.componentStack);
  }

  private reset = () => {
    this.setState({ hasError: false, error: null });
  };

  override render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 400,
            padding: 40,
            fontFamily: '"Microsoft YaHei", Arial, sans-serif',
          }}
        >
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          <h2 style={{ fontSize: 18, margin: '0 0 8px', color: '#eaf4ef' }}>
            页面加载异常
          </h2>
          <p
            style={{
              fontSize: 13,
              color: '#9bb0a8',
              margin: '0 0 24px',
              textAlign: 'center',
              maxWidth: 360,
            }}
          >
            {this.state.error?.message || '渲染过程发生错误，请尝试刷新页面'}
          </p>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={this.reset}
              style={{
                padding: '8px 20px',
                border: '1px solid #68c8a9',
                borderRadius: 6,
                background: '#18221f',
                color: '#68c8a9',
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              重试
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '8px 20px',
                border: 0,
                borderRadius: 6,
                background: '#68c8a9',
                color: '#102019',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 700,
              }}
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
