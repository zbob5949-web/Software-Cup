import { useEffect, useState } from 'react';
import { getAvatarConfig, updateAvatarConfig, type AvatarConfig } from '../../api/admin';

interface Live2DModel {
  model_key: string;
  model_label: string;
  model_dir: string;
  voice_name: string;
  preview_url: string;
  is_active: boolean;
  id?: number;
  name: string;
}

const voiceOptions = [
  { value: 'zh-CN-XiaoyiNeural', label: '晓伊 · 清亮活泼' },
  { value: 'zh-CN-XiaoxiaoNeural', label: '晓晓 · 清新温柔' },
  { value: 'zh-CN-XiaohanNeural', label: '晓涵 · 知性沉稳' },
  { value: 'zh-CN-YunxiNeural', label: '云希 · 亲切男声' },
];

const nativeVoiceOptions = [
  { value: 'zh-CN-XiaoyiNeural', label: '清亮活泼' },
  { value: 'zh-CN-XiaoxiaoNeural', label: '清新温柔' },
  { value: 'zh-CN-XiaohanNeural', label: '中年女播音' },
  { value: 'zh-CN-YunxiNeural', label: '亲切男声' },
];

function voiceToNative(v: string): string {
  if (v.includes('Xiaoxiao')) return '清新温柔';
  if (v.includes('Xiaoyi')) return '清亮活泼';
  if (v.includes('Xiaohan')) return '中年女播音';
  if (v.includes('Yunxi')) return '亲切男声';
  return '清亮活泼';
}

function buildPreviewUrl(modelKey: string, modelDir: string): string {
  return `/live2d/index.html?embed=1&model=${encodeURIComponent(modelDir)}&api=${encodeURIComponent(window.location.origin)}`;
}

export function AvatarManage() {
  const [config, setConfig] = useState<AvatarConfig>({
    name: '灵小游', welcomeMessage: '', introduction: '', videoUrl: '', voiceType: '清亮活泼', speed: 1.0, volume: 0.8,
  });
  const [models, setModels] = useState<Live2DModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      getAvatarConfig(),
      fetch('/api/admin/digital-humans', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('lingshanAdminToken') || ''}` },
      }).then(r => r.json()).then(d => d.data?.items ?? []).catch(() => []),
      fetch('/api/digital-human/catalog').then(r => r.json()).then(d => d.data?.items ?? []).catch(() => []),
    ])
      .then(([avatarData, adminHumans, catalog]) => {
        if (!active) return;
        if (avatarData) {
          setConfig(avatarData);
        }
        // Merge admin data with catalog
        const modelList: Live2DModel[] = (catalog as any[]).map((cat: any) => {
          const admin = (adminHumans as any[]).find((h: any) => h.model_key === cat.model_key);
          return {
            model_key: cat.model_key,
            model_label: cat.model_label,
            model_dir: cat.model_dir || cat.model_key.replace('live2d_', ''),
            voice_name: admin?.voice_name || cat.voice_name || 'zh-CN-XiaoyiNeural',
            preview_url: buildPreviewUrl(cat.model_key, cat.model_dir || cat.model_key.replace('live2d_', '')),
            is_active: admin?.is_active ?? false,
            id: admin?.id,
            name: admin?.name || cat.model_label,
          };
        });
        setModels(modelList);
        setError('');
      })
      .catch(() => { if (active) setError('数字人配置加载失败'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function handleActivate(model: Live2DModel) {
    setSaving(true);
    try {
      if (model.id) {
        // Update existing → set is_active = true
        await fetch(`/api/admin/digital-humans/${model.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('lingshanAdminToken') || ''}`,
          },
          body: JSON.stringify({ is_active: true }),
        });
      } else {
        // Create new config
        await fetch('/api/admin/digital-humans', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('lingshanAdminToken') || ''}`,
          },
          body: JSON.stringify({
            model_key: model.model_key,
            name: model.model_label,
            voice_name: model.voice_name,
            is_active: true,
            appearance: `${model.model_label} Live2D 数字人形象`,
            clothing: '景区导览制服',
            cultural_style: '亲和、适合景区讲解',
            keywords: model.model_label,
          }),
        });
      }
      // Refresh
      setModels(prev => prev.map(m => ({ ...m, is_active: m.model_key === model.model_key })));
      setError('');
    } catch {
      setError('激活失败');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="admin-page-avatar"><div className="admin-table-empty">正在加载...</div></div>;

  return (
    <div className="admin-page-avatar">
      <div className="admin-page-header">
        <h2>数字人管理</h2>
        <p className="admin-page-subtitle">选择并激活 Live2D 数字人形象，游客端自动切换</p>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        {models.map((model) => (
          <div
            key={model.model_key}
            style={{
              border: model.is_active ? '2px solid #68c8a9' : '1px solid #e0e0e0',
              borderRadius: 12,
              padding: 16,
              background: model.is_active ? '#e8f5e9' : '#fff',
              cursor: 'pointer',
              transition: 'all .2s',
              position: 'relative',
            }}
          >
            {model.is_active && (
              <span style={{
                position: 'absolute', top: 8, right: 8,
                background: '#68c8a9', color: '#fff', padding: '2px 10px',
                borderRadius: 4, fontSize: 12, fontWeight: 700,
              }}>
                当前激活
              </span>
            )}
            <div style={{
              width: '100%', height: 220, background: '#f5f5f5',
              borderRadius: 8, overflow: 'hidden', marginBottom: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <iframe
                src={model.preview_url}
                style={{ width: '100%', height: '100%', border: 0, background: 'transparent' }}
                title={model.model_label}
                allow="autoplay"
              />
            </div>
            <h3 style={{ margin: '0 0 4px', fontSize: 16 }}>{model.name}</h3>
            <p style={{ margin: '0 0 12px', fontSize: 13, color: '#666' }}>
              {voiceToNative(model.voice_name)}
            </p>
            <button
              className={model.is_active ? 'admin-btn admin-btn-secondary' : 'admin-btn admin-btn-primary'}
              disabled={model.is_active || saving}
              onClick={(e) => { e.stopPropagation(); handleActivate(model); }}
              style={{ width: '100%' }}
            >
              {model.is_active ? '已激活' : saving ? '激活中...' : '激活此形象'}
            </button>
          </div>
        ))}
      </div>

      {/* Voice + basic settings (fallback for edge cases) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="admin-card">
          <div className="admin-card-header"><h3>语音配置</h3></div>
          <div className="admin-card-body">
            <div className="admin-form-group">
              <label className="admin-form-label">声音类型</label>
              <select className="admin-form-select" value={config.voiceType} onChange={(event) => setConfig((current) => ({ ...current, voiceType: event.target.value }))}>
                {nativeVoiceOptions.map((voice) => <option key={voice.value} value={voice.value}>{voice.label}</option>)}
              </select>
              <button type="button" className="admin-btn admin-btn-primary" onClick={() => void updateAvatarConfig({ name: config.name, welcome_message: config.welcomeMessage, introduction: config.introduction, video_url: config.videoUrl, voice_type: config.voiceType, speed: config.speed, volume: config.volume })}>保存音色</button>
            </div>
            <div className="admin-form-group">
              <label className="admin-form-label">语速 {config.speed.toFixed(1)}x</label>
              <input type="range" min="0.5" max="2.0" step="0.1" value={config.speed} onChange={(event) => setConfig((current) => ({ ...current, speed: parseFloat(event.target.value) }))} className="admin-range-input" />
            </div>
            <div className="admin-form-group">
              <label className="admin-form-label">音量 {Math.round(config.volume * 100)}%</label>
              <input type="range" min="0" max="1" step="0.05" value={config.volume} onChange={(event) => setConfig((current) => ({ ...current, volume: parseFloat(event.target.value) }))} className="admin-range-input" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-header"><h3>基本信息</h3></div>
          <div className="admin-card-body">
            <div className="admin-config-item">
              <span className="admin-config-label">名称</span>
              <span>{config.name}</span>
            </div>
            <div className="admin-config-item">
              <span className="admin-config-label">欢迎语</span>
              <span>{config.welcomeMessage || '你好，我是灵小游，很高兴为你服务！'}</span>
            </div>
            <div className="admin-config-item">
              <span className="admin-config-label">介绍</span>
              <span>{config.introduction || '灵山景区 AI 数字人导游'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
