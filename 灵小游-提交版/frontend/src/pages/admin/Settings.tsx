import { useEffect, useState } from 'react';
import {
  getSettings,
  updateApiConfig,
  updateSystemInfo,
  type ApiConfig,
  type SystemInfo,
} from '../../api/admin';

const emptySystemInfo: SystemInfo = {
  systemName: '',
  contactPhone: '',
  contactEmail: '',
  copyright: '',
  beian: '',
};

const emptyApiConfig: ApiConfig = {
  weatherApi: '',
  weatherKey: '',
  llmApi: '',
  llmModel: '',
  dbHost: '',
  dbPort: '',
  dbName: '',
  dbUser: '',
  dbPassword: '',
};

export function Settings() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo>(emptySystemInfo);
  const [apiConfig, setApiConfig] = useState<ApiConfig>(emptyApiConfig);
  const [editingSystem, setEditingSystem] = useState(false);
  const [editingApi, setEditingApi] = useState(false);
  const [systemForm, setSystemForm] = useState<SystemInfo>(emptySystemInfo);
  const [apiForm, setApiForm] = useState<ApiConfig>(emptyApiConfig);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    getSettings()
      .then((data) => {
        if (!active) return;
        if (!data) {
          setError('系统设置加载失败');
          return;
        }
        setSystemInfo(data.systemInfo ?? emptySystemInfo);
        setApiConfig(data.apiConfig ?? emptyApiConfig);
        setSystemForm(data.systemInfo ?? emptySystemInfo);
        setApiForm(data.apiConfig ?? emptyApiConfig);
      })
      .catch(() => {
        if (!active) return;
        setError('系统设置加载失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleSaveSystem = async () => {
    try {
      await updateSystemInfo({
        system_name: systemForm.systemName,
        contact_phone: systemForm.contactPhone,
        contact_email: systemForm.contactEmail,
        copyright: systemForm.copyright,
        beian: systemForm.beian,
      });
      setSystemInfo(systemForm);
      setEditingSystem(false);
      setError('');
    } catch {
      setError('保存系统基础信息失败');
    }
  };

  const handleSaveApi = async () => {
    try {
      await updateApiConfig({
        weather_api: apiForm.weatherApi,
        weather_key: apiForm.weatherKey,
        llm_api: apiForm.llmApi,
        llm_model: apiForm.llmModel,
        db_host: apiForm.dbHost,
        db_port: apiForm.dbPort,
        db_name: apiForm.dbName,
        db_user: apiForm.dbUser,
        db_password: apiForm.dbPassword,
      });
      setApiConfig(apiForm);
      setEditingApi(false);
      setError('');
    } catch {
      setError('保存接口配置失败');
    }
  };

  return (
    <div className="admin-page-settings">
      <div className="admin-page-header">
        <h2>系统设置</h2>
        <p className="admin-page-subtitle">管理系统基础信息、接口配置与连接参数</p>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}
      {loading ? <div className="admin-table-empty">正在加载配置...</div> : null}

      <div className="admin-card">
        <div className="admin-card-header">
          <h3>基础信息</h3>
          {!editingSystem ? (
            <button
              className="admin-btn admin-btn-secondary admin-btn-sm"
              onClick={() => {
                setSystemForm({ ...systemInfo });
                setEditingSystem(true);
              }}
            >
              编辑
            </button>
          ) : null}
        </div>
        <div className="admin-card-body">
          {editingSystem ? (
            <div className="admin-settings-form">
              <div className="admin-form-group">
                <label className="admin-form-label">系统名称</label>
                <input className="admin-form-input" type="text" value={systemForm.systemName} onChange={(e) => setSystemForm({ ...systemForm, systemName: e.target.value })} />
              </div>
              <div className="admin-form-row">
                <div className="admin-form-group">
                  <label className="admin-form-label">联系电话</label>
                  <input className="admin-form-input" type="text" value={systemForm.contactPhone} onChange={(e) => setSystemForm({ ...systemForm, contactPhone: e.target.value })} />
                </div>
                <div className="admin-form-group">
                  <label className="admin-form-label">联系邮箱</label>
                  <input className="admin-form-input" type="email" value={systemForm.contactEmail} onChange={(e) => setSystemForm({ ...systemForm, contactEmail: e.target.value })} />
                </div>
              </div>
              <div className="admin-form-group">
                <label className="admin-form-label">版权信息</label>
                <input className="admin-form-input" type="text" value={systemForm.copyright} onChange={(e) => setSystemForm({ ...systemForm, copyright: e.target.value })} />
              </div>
              <div className="admin-form-group">
                <label className="admin-form-label">备案号</label>
                <input className="admin-form-input" type="text" value={systemForm.beian} onChange={(e) => setSystemForm({ ...systemForm, beian: e.target.value })} />
              </div>
              <div className="admin-form-actions">
                <button className="admin-btn admin-btn-secondary" onClick={() => setEditingSystem(false)}>
                  取消
                </button>
                <button className="admin-btn admin-btn-primary" onClick={handleSaveSystem}>
                  保存
                </button>
              </div>
            </div>
          ) : (
            <div className="admin-settings-display">
              <div className="admin-config-item">
                <span className="admin-config-label">系统名称</span>
                <span>{systemInfo.systemName}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">联系电话</span>
                <span>{systemInfo.contactPhone}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">联系邮箱</span>
                <span>{systemInfo.contactEmail}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">版权信息</span>
                <span>{systemInfo.copyright}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">备案号</span>
                <span>{systemInfo.beian}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-card-header">
          <h3>API 配置</h3>
          {!editingApi ? (
            <button
              className="admin-btn admin-btn-secondary admin-btn-sm"
              onClick={() => {
                setApiForm({ ...apiConfig });
                setEditingApi(true);
              }}
            >
              编辑
            </button>
          ) : null}
        </div>
        <div className="admin-card-body">
          {editingApi ? (
            <div className="admin-settings-form">
              <h4 className="admin-form-section-title">天气服务</h4>
              <div className="admin-form-group">
                <label className="admin-form-label">API 地址</label>
                <input className="admin-form-input" type="text" value={apiForm.weatherApi} onChange={(e) => setApiForm({ ...apiForm, weatherApi: e.target.value })} />
              </div>
              <div className="admin-form-group">
                <label className="admin-form-label">API Key</label>
                <input className="admin-form-input" type="password" value={apiForm.weatherKey} onChange={(e) => setApiForm({ ...apiForm, weatherKey: e.target.value })} />
              </div>

              <h4 className="admin-form-section-title">大模型服务</h4>
              <div className="admin-form-group">
                <label className="admin-form-label">API 地址</label>
                <input className="admin-form-input" type="text" value={apiForm.llmApi} onChange={(e) => setApiForm({ ...apiForm, llmApi: e.target.value })} />
              </div>
              <div className="admin-form-group">
                <label className="admin-form-label">模型</label>
                <input className="admin-form-input" type="text" value={apiForm.llmModel} onChange={(e) => setApiForm({ ...apiForm, llmModel: e.target.value })} />
              </div>

              <h4 className="admin-form-section-title">数据连接</h4>
              <div className="admin-form-row">
                <div className="admin-form-group">
                  <label className="admin-form-label">主机</label>
                  <input className="admin-form-input" type="text" value={apiForm.dbHost} onChange={(e) => setApiForm({ ...apiForm, dbHost: e.target.value })} />
                </div>
                <div className="admin-form-group">
                  <label className="admin-form-label">端口</label>
                  <input className="admin-form-input" type="text" value={apiForm.dbPort} onChange={(e) => setApiForm({ ...apiForm, dbPort: e.target.value })} />
                </div>
              </div>
              <div className="admin-form-group">
                <label className="admin-form-label">数据库名</label>
                <input className="admin-form-input" type="text" value={apiForm.dbName} onChange={(e) => setApiForm({ ...apiForm, dbName: e.target.value })} />
              </div>
              <div className="admin-form-row">
                <div className="admin-form-group">
                  <label className="admin-form-label">用户名</label>
                  <input className="admin-form-input" type="text" value={apiForm.dbUser} onChange={(e) => setApiForm({ ...apiForm, dbUser: e.target.value })} />
                </div>
                <div className="admin-form-group">
                  <label className="admin-form-label">密码</label>
                  <input className="admin-form-input" type="password" value={apiForm.dbPassword} onChange={(e) => setApiForm({ ...apiForm, dbPassword: e.target.value })} />
                </div>
              </div>
              <div className="admin-form-actions">
                <button className="admin-btn admin-btn-secondary" onClick={() => setEditingApi(false)}>
                  取消
                </button>
                <button className="admin-btn admin-btn-primary" onClick={handleSaveApi}>
                  保存
                </button>
              </div>
            </div>
          ) : (
            <div className="admin-settings-display">
              <h4 className="admin-form-section-title">天气服务</h4>
              <div className="admin-config-item">
                <span className="admin-config-label">API 地址</span>
                <span className="admin-config-mono">{apiConfig.weatherApi}</span>
              </div>

              <h4 className="admin-form-section-title" style={{ marginTop: 20 }}>
                大模型服务
              </h4>
              <div className="admin-config-item">
                <span className="admin-config-label">API 地址</span>
                <span className="admin-config-mono">{apiConfig.llmApi}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">当前模型</span>
                <span className="admin-config-mono">{apiConfig.llmModel}</span>
              </div>

              <h4 className="admin-form-section-title" style={{ marginTop: 20 }}>
                数据连接
              </h4>
              <div className="admin-config-item">
                <span className="admin-config-label">主机</span>
                <span>{apiConfig.dbHost}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">端口</span>
                <span>{apiConfig.dbPort}</span>
              </div>
              <div className="admin-config-item">
                <span className="admin-config-label">数据库</span>
                <span>{apiConfig.dbName}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
