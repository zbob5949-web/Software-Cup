export type Locale = 'zh-CN' | 'en-US';

type MessageKey =
  | 'username.label'
  | 'username.placeholder'
  | 'username.required'
  | 'username.invalid'
  | 'username.valid'
  | 'password.label'
  | 'password.placeholder'
  | 'password.required'
  | 'password.invalid'
  | 'password.ruleSummary'
  | 'password.rule.length'
  | 'password.rule.uppercase'
  | 'password.rule.number'
  | 'password.rule.special'
  | 'password.show'
  | 'password.hide'
  | 'password.strength.weak'
  | 'password.strength.medium'
  | 'password.strength.strong'
  | 'register.title'
  | 'register.subtitle'
  | 'register.button'
  | 'register.loading'
  | 'register.loginHint'
  | 'register.loginLink'
  | 'login.title'
  | 'login.subtitle'
  | 'login.usernamePlaceholder'
  | 'login.passwordPlaceholder'
  | 'login.button'
  | 'login.loading'
  | 'login.success'
  | 'login.invalid'
  | 'login.serverError'
  | 'login.registerHint'
  | 'login.registerLink'
  | 'login.chatLink'
  | 'chat.title'
  | 'chat.subtitle'
  | 'chat.inputPlaceholder'
  | 'chat.empty'
  | 'chat.send'
  | 'chat.stop'
  | 'chat.clear'
  | 'chat.loading'
  | 'chat.loginNotice'
  | 'chat.loggedInAs'
  | 'chat.goLogin'
  | 'chat.logout'
  | 'chat.reask'
  | 'chat.quick.open'
  | 'chat.quick.route'
  | 'chat.quick.spots'
  | 'chat.quick.ticket'
  | 'chat.error.empty'
  | 'chat.error.loginRequired'
  | 'chat.error.failed'
  | 'chat.stopped'
  | 'toast.success'
  | 'toast.badRequest'
  | 'toast.conflict'
  | 'toast.serverError'
  | 'toast.networkError'
  | 'toast.unknown'
  | 'success.redirect';

const messages: Record<Locale, Record<MessageKey, string>> = {
  'zh-CN': {
    'username.label': '用户名',
    'username.placeholder': '请输入 3-20 位用户名',
    'username.required': '请输入用户名',
    'username.invalid': '3-20 位，支持字母、数字和 ._-',
    'username.valid': '用户名格式正确',
    'password.label': '密码',
    'password.placeholder': '请输入符合规则的密码',
    'password.required': '请输入密码',
    'password.invalid': '至少 8 位，需含大小写字母、数字和特殊字符',
    'password.ruleSummary': '至少 8 位，需包含大写字母、小写字母、数字和特殊符号',
    'password.rule.length': '至少 8 位',
    'password.rule.uppercase': '包含大写字母',
    'password.rule.number': '包含数字',
    'password.rule.special': '包含特殊符号',
    'password.show': '显示密码',
    'password.hide': '隐藏密码',
    'password.strength.weak': '弱',
    'password.strength.medium': '中',
    'password.strength.strong': '强',
    'register.title': '创建你的账号',
    'register.subtitle': '输入信息后即可完成注册',
    'register.button': '立即注册',
    'register.loading': '注册中',
    'register.loginHint': '已有账号？',
    'register.loginLink': '立即登录',
    'login.title': '登录页',
    'login.subtitle': '登录后即可使用 AI 景区智能问答',
    'login.usernamePlaceholder': '请输入用户名',
    'login.passwordPlaceholder': '请输入登录密码',
    'login.button': '立即登录',
    'login.loading': '登录中',
    'login.success': '登录成功，开始提问吧',
    'login.invalid': '用户名或密码错误',
    'login.serverError': '登录失败，请稍后再试',
    'login.registerHint': '还没有账号？',
    'login.registerLink': '去注册',
    'login.chatLink': '进入 AI 对话',
    'chat.title': 'AI 智能助手',
    'chat.subtitle': '可回答景区开放时间、景点介绍、路线推荐等问题',
    'chat.inputPlaceholder': '请输入你想咨询的问题',
    'chat.empty': '你可以问我开放时间、景点介绍、路线推荐等问题',
    'chat.send': '发送',
    'chat.stop': '停止回答',
    'chat.clear': '清空对话',
    'chat.loading': 'AI 正在思考...',
    'chat.loginNotice': '登录后可使用完整 AI 对话功能',
    'chat.loggedInAs': '当前账号',
    'chat.goLogin': '去登录',
    'chat.logout': '退出登录',
    'chat.reask': '重新提问',
    'chat.quick.open': '今天开放吗？',
    'chat.quick.route': '推荐游玩路线',
    'chat.quick.spots': '景点有哪些？',
    'chat.quick.ticket': '门票怎么预约？',
    'chat.error.empty': '请输入问题内容',
    'chat.error.loginRequired': '请先登录',
    'chat.error.failed': '请求失败，请稍后再试',
    'chat.stopped': '已停止当前提问',
    'toast.success': '注册成功',
    'toast.badRequest': '提交参数有误，请检查输入内容',
    'toast.conflict': '用户名已存在，请更换后重试',
    'toast.serverError': '服务器异常，请稍后再试',
    'toast.networkError': '网络请求失败，请检查网络连接',
    'toast.unknown': '发生未知错误，请稍后重试',
    'success.redirect': '注册成功，正在跳转到登录页',
  },
  'en-US': {
    'username.label': 'Username',
    'username.placeholder': 'Enter a 3-20 character username',
    'username.required': 'Username is required',
    'username.invalid': 'Use 3-20 letters, numbers, or ._-',
    'username.valid': 'Username looks good',
    'password.label': 'Password',
    'password.placeholder': 'Enter a secure password',
    'password.required': 'Password is required',
    'password.invalid': 'At least 8 chars with upper, lower, number, and symbol',
    'password.ruleSummary': 'At least 8 chars with upper, lower, number, and symbol',
    'password.rule.length': 'At least 8 chars',
    'password.rule.uppercase': 'Uppercase letter',
    'password.rule.number': 'Number',
    'password.rule.special': 'Special symbol',
    'password.show': 'Show password',
    'password.hide': 'Hide password',
    'password.strength.weak': 'Weak',
    'password.strength.medium': 'Medium',
    'password.strength.strong': 'Strong',
    'register.title': 'Create your account',
    'register.subtitle': 'Fill in your information to create an account',
    'register.button': 'Register',
    'register.loading': 'Registering',
    'register.loginHint': 'Already have an account?',
    'register.loginLink': 'Sign in',
    'login.title': 'Login',
    'login.subtitle': 'Sign in to use the AI scenic assistant',
    'login.usernamePlaceholder': 'Enter your username',
    'login.passwordPlaceholder': 'Enter your password',
    'login.button': 'Sign in',
    'login.loading': 'Signing in',
    'login.success': 'Login successful, start asking',
    'login.invalid': 'Invalid username or password',
    'login.serverError': 'Login failed, please try again later',
    'login.registerHint': 'Need an account?',
    'login.registerLink': 'Register',
    'login.chatLink': 'Open AI chat',
    'chat.title': 'AI Assistant',
    'chat.subtitle': 'Ask about opening hours, attractions, routes, and more',
    'chat.inputPlaceholder': 'Enter your question',
    'chat.empty': 'Ask about opening hours, attractions, routes, and more',
    'chat.send': 'Send',
    'chat.stop': 'Stop',
    'chat.clear': 'Clear chat',
    'chat.loading': 'AI is thinking...',
    'chat.loginNotice': 'Sign in to unlock the full AI chat experience',
    'chat.loggedInAs': 'Signed in as',
    'chat.goLogin': 'Go to login',
    'chat.logout': 'Sign out',
    'chat.reask': 'Ask again',
    'chat.quick.open': 'Is it open today?',
    'chat.quick.route': 'Recommend a route',
    'chat.quick.spots': 'What attractions are there?',
    'chat.quick.ticket': 'How do I book tickets?',
    'chat.error.empty': 'Please enter a question',
    'chat.error.loginRequired': 'Please log in first',
    'chat.error.failed': 'Request failed, please try again later',
    'chat.stopped': 'The current request was stopped',
    'toast.success': 'Registration succeeded',
    'toast.badRequest': 'Invalid request parameters',
    'toast.conflict': 'This username already exists',
    'toast.serverError': 'Server error, please try again later',
    'toast.networkError': 'Network request failed, please check your connection',
    'toast.unknown': 'Unknown error, please try again later',
    'success.redirect': 'Registration succeeded, redirecting to login',
  },
};

export function getLocale(): Locale {
  return navigator.language === 'en-US' ? 'en-US' : 'zh-CN';
}

export function t(key: MessageKey, locale = getLocale()): string {
  return messages[locale][key];
}
