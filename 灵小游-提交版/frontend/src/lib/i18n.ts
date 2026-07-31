export type Locale = 'zh-CN' | 'en-US';

type MessageKey =
  | 'app.title'
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
  | 'register.featureNote'
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
  | 'login.guestEntry'
  | 'login.welcomeBack'
  | 'login.welcomeBackSub'
  | 'login.phoneLabel'
  | 'login.phonePlaceholder'
  | 'login.phoneRequired'
  | 'login.phoneInvalid'
  | 'login.forgotPassword'
  | 'login.smsLoginTab'
  | 'login.passwordLoginTab'
  | 'login.smsCodeLabel'
  | 'login.smsCodePlaceholder'
  | 'login.getSmsCode'
  | 'login.smsNotAvailable'
  | 'register.welcomeTitle'
  | 'register.welcomeSubtitle2'
  | 'register.phoneLabel'
  | 'register.phonePlaceholder'
  | 'register.smsCodeLabel'
  | 'register.smsCodePlaceholder'
  | 'register.getSmsCode'
  | 'register.smsRetry'
  | 'register.confirmPasswordLabel'
  | 'register.confirmPasswordPlaceholder'
  | 'register.passwordMismatch'
  | 'register.agreePrefix'
  | 'register.terms'
  | 'register.and'
  | 'register.privacy'
  | 'register.agreementRequired'
  | 'register.otherLoginMethods'
  | 'register.wechat'
  | 'register.qq'
  | 'register.thirdPartyWechatHint'
  | 'register.thirdPartyQQHint'
  | 'register.smsNotAvailable'
  | 'forgot.title'
  | 'forgot.subtitle'
  | 'forgot.phoneLabel'
  | 'forgot.phonePlaceholder'
  | 'forgot.smsCodeLabel'
  | 'forgot.smsCodePlaceholder'
  | 'forgot.getSmsCode'
  | 'forgot.smsRetry'
  | 'forgot.newPasswordLabel'
  | 'forgot.newPasswordPlaceholder'
  | 'forgot.confirmPasswordLabel'
  | 'forgot.confirmPasswordPlaceholder'
  | 'forgot.passwordMismatch'
  | 'forgot.button'
  | 'forgot.loading'
  | 'forgot.success'
  | 'forgot.backToLogin'
  | 'forgot.smsNotAvailable'
  | 'login.brandTitle'
  | 'login.brandSubtitle'
  | 'login.routeTitle'
  | 'login.routeCard'
  | 'login.routeDesc'
  | 'login.welcome'
  | 'login.welcomeSubtitle'
  | 'chat.title'
  | 'chat.subtitle'
  | 'chat.inputPlaceholder'
  | 'chat.empty'
  | 'chat.send'
  | 'chat.stop'
  | 'chat.clear'
  | 'chat.loading'
  | 'chat.aiLoading'
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
  | 'chat.digitalName'
  | 'chat.digitalStatus'
  | 'chat.voiceOn'
  | 'chat.voiceOff'
  | 'chat.location'
  | 'chat.voiceInput'
  | 'chat.onlineStatus'
  | 'chat.voiceStatus'
  | 'chat.kbStatus'
  | 'chat.scenicToday'
  | 'chat.scenicOpen'
  | 'chat.scenicRoute'
  | 'chat.scenicCrowd'
  | 'chat.scenicHotSpots'
  | 'chat.scenicRoutes'
  | 'chat.scenicLocation'
  | 'chat.scenicLocationHint'
  | 'chat.routeHalf'
  | 'chat.routeCulture'
  | 'chat.routeFamily'
  | 'chat.routeTime'
  | 'chat.routeCrowd'
  | 'chat.routeReason'
  | 'chat.routeSteps'
  | 'chat.spotBuddha'
  | 'chat.spotJiulong'
  | 'chat.spotFangong'
  | 'chat.spotWuyin'
  | 'chat.locEntrance'
  | 'chat.locJiulong'
  | 'chat.locBuddha'
  | 'chat.locFangong'
  | 'chat.scenicInfo'
  | 'drawer.close'
  | 'toast.success'
  | 'toast.badRequest'
  | 'toast.conflict'
  | 'toast.serverError'
  | 'toast.networkError'
  | 'toast.unknown'
  | 'success.redirect'
  | 'home.welcome'
  | 'home.weatherTitle'
  | 'home.weatherAdvice'
  | 'home.weatherTag'
  | 'home.aiEntryTitle'
  | 'home.aiEntrySub'
  | 'home.aiEntryNote'
  | 'home.aiEntryAction'
  | 'home.inputPlaceholder'
  | 'home.services.spots'
  | 'home.services.guide'
  | 'home.services.routes'
  | 'home.services.feedback'
  | 'home.services.spotsDesc'
  | 'home.services.guideDesc'
  | 'home.services.routesDesc'
  | 'home.services.feedbackDesc'
  | 'nav.home'
  | 'nav.guide'
  | 'nav.aiGuide'
  | 'nav.profile'
  | 'guide.pageTitle'
  | 'guide.pageDesc'
  | 'guide.tabMap'
  | 'guide.tabRoutes'
  | 'guide.mapCardTitle'
  | 'guide.mapCardDesc'
  | 'guide.mapHint'
  | 'guide.scenicTitle'
  | 'guide.scenicDesc'
  | 'guide.nearbyTitle'
  | 'guide.nearbyDesc'
  | 'guide.voiceTitle'
  | 'guide.voiceDesc'
  | 'guide.locationTitle'
  | 'guide.locationDesc'
  | 'guide.routeSmartTitle'
  | 'guide.routeSmartDesc'
  | 'guide.routeTag'
  | 'guide.routeDayTitle'
  | 'guide.routeNatureTitle'
  | 'guide.routeHalfDesc'
  | 'guide.routeDayDesc'
  | 'guide.routeFamilyDesc'
  | 'guide.routeCultureDesc'
  | 'guide.routeNatureDesc'
  | 'profile.title'
  | 'profile.guestTitle'
  | 'profile.guestSub'
  | 'profile.memberDesc'
  | 'profile.serviceTitle'
  | 'profile.serviceDesc'
  | 'profile.faq'
  | 'profile.favorites'
  | 'profile.orders'
  | 'profile.history'
  | 'profile.qa'
  | 'profile.feedback'
  | 'profile.settings'
  | 'profile.about'
  | 'profile.loginPrompt'
  | 'profile.logout'
  | 'aiChat.title'
  | 'aiChat.back'
  | 'aiChat.topTag'
  | 'aiChat.voiceEntry'
  | 'aiChat.syncStatus'
  | 'aiChat.thinking'
  | 'aiChat.listening'
  | 'aiChat.tapToSpeak'
  | 'aiChat.digitalIntro'
  | 'voice.recording'
  | 'voice.cancel'
  | 'voice.recognizing'
  | 'voice.error'
  | 'voice.holdToSpeak'
  | 'voice.releaseToSend'
  | 'voice.permissionDenied'
  | 'voice.micBusy'
  | 'voice.micUnavailable'
  | 'voice.slideUpCancel'
  | 'voice.releaseCancel';

const messages: Record<Locale, Record<MessageKey, string>> = {
  'zh-CN': {
    'app.title': '灵山智游 AI 数字导览助手',
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
    'register.title': '开启灵山智慧之旅',
    'register.subtitle': '注册后即可获得专属 AI 导览、路线推荐与景点讲解服务',
    'register.button': '注册',
    'register.loading': '注册中...',
    'register.loginHint': '已有账号？',
    'register.loginLink': '立即登录',
    'register.featureNote': '注册后可体验智能问答、语音导览、个性化路线推荐等服务',
    'register.welcomeTitle': '欢迎注册',
    'register.welcomeSubtitle2': '创建账号，开启智能服务',
    'register.phoneLabel': '手机号',
    'register.phonePlaceholder': '请输入手机号',
    'register.smsCodeLabel': '验证码',
    'register.smsCodePlaceholder': '请输入验证码',
    'register.getSmsCode': '获取验证码',
    'register.smsRetry': 's后重新获取',
    'register.confirmPasswordLabel': '确认密码',
    'register.confirmPasswordPlaceholder': '请再次输入密码',
    'register.passwordMismatch': '两次密码不一致',
    'register.agreePrefix': '我已阅读并同意',
    'register.terms': '用户协议',
    'register.and': '和',
    'register.privacy': '隐私政策',
    'register.agreementRequired': '请先阅读并同意用户协议和隐私政策',
    'register.otherLoginMethods': '其他方式注册/登录',
    'register.wechat': '微信',
    'register.qq': 'QQ',
    'register.thirdPartyWechatHint': '微信授权登录功能待接入',
    'register.thirdPartyQQHint': 'QQ授权登录功能待接入',
    'register.smsNotAvailable': '验证码功能待接入',
    'login.title': '登录页',
    'login.subtitle': '登录后即可使用 AI 景区智能问答',
    'login.usernamePlaceholder': '请输入用户名',
    'login.passwordPlaceholder': '请输入登录密码',
    'login.button': '登录',
    'login.loading': '登录中...',
    'login.success': '登录成功，开始提问吧',
    'login.invalid': '账号或密码错误，请重新输入',
    'login.serverError': '登录失败，请稍后再试',
    'login.registerHint': '还没有账号？',
    'login.registerLink': '去注册',
    'login.chatLink': '进入 AI 对话',
    'login.guestEntry': '游客体验模式',
    'login.welcomeBack': '欢迎回来',
    'login.welcomeBackSub': '请登录后继续使用服务',
    'login.phoneLabel': '手机号/账号',
    'login.phonePlaceholder': '请输入手机号或账号',
    'login.phoneRequired': '请输入手机号或账号',
    'login.phoneInvalid': '请输入正确的手机号',
    'login.forgotPassword': '忘记密码？',
    'login.smsLoginTab': '验证码登录',
    'login.passwordLoginTab': '密码登录',
    'login.smsCodeLabel': '验证码',
    'login.smsCodePlaceholder': '请输入验证码',
    'login.getSmsCode': '获取验证码',
    'login.smsNotAvailable': '验证码登录功能待接入',
    'login.brandTitle': '灵山智游',
    'login.brandSubtitle': '山水有声，文化有答，让 AI 数字导游陪你走进灵山',
    'login.routeTitle': '今日推荐路线',
    'login.routeCard': '入口广场 → 九龙灌浴 → 灵山大佛 → 梵宫 → 五印坛城',
    'login.routeDesc': '经典半日游 · 适合首次游览游客 · 预计 3-4 小时',
    'login.welcome': '欢迎来到灵山智游',
    'login.welcomeSubtitle': '登录后即可体验 AI 问答、语音导览与个性化路线推荐',
    'forgot.title': '忘记密码',
    'forgot.subtitle': '请输入注册手机号以重置密码',
    'forgot.phoneLabel': '手机号',
    'forgot.phonePlaceholder': '请输入注册手机号',
    'forgot.smsCodeLabel': '验证码',
    'forgot.smsCodePlaceholder': '请输入验证码',
    'forgot.getSmsCode': '获取验证码',
    'forgot.smsRetry': 's后重新获取',
    'forgot.newPasswordLabel': '新密码',
    'forgot.newPasswordPlaceholder': '请输入新密码',
    'forgot.confirmPasswordLabel': '确认密码',
    'forgot.confirmPasswordPlaceholder': '请再次输入新密码',
    'forgot.passwordMismatch': '两次密码不一致',
    'forgot.button': '确认修改',
    'forgot.loading': '修改中...',
    'forgot.success': '密码修改成功，请重新登录',
    'forgot.backToLogin': '返回登录',
    'forgot.smsNotAvailable': '验证码功能待接入',
    'chat.title': '灵山 AI 数字导游 · 小灵',
    'chat.subtitle': '可为你讲解灵山文化、推荐游览路线、回答景区问题',
    'chat.inputPlaceholder': '请输入你想咨询的灵山景区问题，例如"帮我规划半日游路线"',
    'chat.empty': '你好，我是灵山 AI 数字导游小灵。你可以问我景点故事、开放时间、游览路线、门票预约等问题。',
    'chat.send': '发送',
    'chat.stop': '停止回答',
    'chat.clear': '清空对话',
    'chat.loading': 'AI 正在思考...',
    'chat.aiLoading': '小灵正在检索景区知识库……',
    'chat.loginNotice': '登录后可使用完整 AI 对话功能',
    'chat.loggedInAs': '当前账号',
    'chat.goLogin': '去登录',
    'chat.logout': '退出登录',
    'chat.reask': '重新提问',
    'chat.quick.open': '今天开放吗？',
    'chat.quick.route': '帮我规划 2 小时游览路线',
    'chat.quick.spots': '灵山大佛有什么故事？',
    'chat.quick.ticket': '九龙灌浴什么时候开始？',
    'chat.error.empty': '请输入问题内容',
    'chat.error.loginRequired': '请先登录',
    'chat.error.failed': '请求失败，请稍后再试',
    'chat.stopped': '已停止当前提问',
    'chat.digitalName': '小灵',
    'chat.digitalStatus': '正在为你讲解灵山景区',
    'chat.voiceOn': '开启语音',
    'chat.voiceOff': '停止播报',
    'chat.location': '定位',
    'chat.voiceInput': '语音输入',
    'chat.onlineStatus': 'AI 数字导游在线',
    'chat.voiceStatus': '支持语音问答',
    'chat.kbStatus': '基于景区知识库',
    'chat.scenicToday': '今日导览',
    'chat.scenicOpen': '开放状态：以景区公告为准',
    'chat.scenicRoute': '推荐路线：经典半日游',
    'chat.scenicCrowd': '适合人群：首次游览、家庭出行、文化体验',
    'chat.scenicHotSpots': '热门景点',
    'chat.scenicRoutes': '推荐路线',
    'chat.scenicLocation': '定位辅助',
    'chat.scenicLocationHint': '如果 GPS 信号较弱，可手动选择当前位置。',
    'chat.routeHalf': '经典半日游',
    'chat.routeCulture': '文化深度游',
    'chat.routeFamily': '亲子轻松游',
    'chat.routeTime': '预计时长',
    'chat.routeCrowd': '适合人群',
    'chat.routeReason': '推荐理由',
    'chat.routeSteps': '路线',
    'chat.spotBuddha': '灵山大佛',
    'chat.spotJiulong': '九龙灌浴',
    'chat.spotFangong': '梵宫',
    'chat.spotWuyin': '五印坛城',
    'chat.locEntrance': '入口广场',
    'chat.locJiulong': '九龙灌浴',
    'chat.locBuddha': '灵山大佛',
    'chat.locFangong': '梵宫',
    'chat.scenicInfo': '景区信息',
    'drawer.close': '关闭',
    'toast.success': '注册成功',
    'toast.badRequest': '提交参数有误，请检查输入内容',
    'toast.conflict': '用户名已存在，请更换后重试',
    'toast.serverError': '服务器异常，请稍后再试',
    'toast.networkError': '网络请求失败，请检查网络连接',
    'toast.unknown': '发生未知错误，请稍后重试',
    'success.redirect': '注册成功，正在跳转到登录页',
    'home.welcome': '你好，欢迎来到灵山景区',
    'home.weatherTitle': '无锡灵山',
    'home.weatherAdvice': '适宜游览，建议做好防晒',
    'home.weatherTag': '今日建议',
    'home.aiEntryTitle': '我是灵山智能导览助手',
    'home.aiEntrySub': '点击与我交流',
    'home.aiEntryNote': '支持景点讲解、游览路线推荐、语音问答与游客服务咨询。',
    'home.aiEntryAction': '点击进入 AI 导游',
    'home.inputPlaceholder': '问问灵山智能导览助手...',
    'home.services.spots': '景点介绍',
    'home.services.guide': '智能导览',
    'home.services.routes': '推荐路线',
    'home.services.feedback': '游客反馈',
    'home.services.spotsDesc': '查看灵山主要景点与讲解',
    'home.services.guideDesc': '查看地图、定位与附近景点',
    'home.services.routesDesc': '推荐半日游、一日游路线',
    'home.services.feedbackDesc': '提交建议，查看个人服务',
    'nav.home': '首页',
    'nav.guide': '导览',
    'nav.aiGuide': 'AI导游',
    'nav.profile': '我的',
    'guide.pageTitle': '景区导览与路线推荐',
    'guide.pageDesc': '融合地图导览、景点介绍、当前位置与游览路线的移动端导览页面。',
    'guide.tabMap': '景区地图',
    'guide.tabRoutes': '推荐路线',
    'guide.mapCardTitle': '景区地图导览',
    'guide.mapCardDesc': '查看景点点位、当前位置和附近服务，快速进入语音讲解。',
    'guide.mapHint': '支持景点点位浏览、当前位置查看与手动选择景点入口。',
    'guide.scenicTitle': '灵山胜境景区导览',
    'guide.scenicDesc': '灵山胜境是世界佛教论坛永久会址，拥有 88 米高的灵山大佛、宏伟的梵宫、九龙灌浴等著名景点，建议游玩 4-6 小时。',
    'guide.nearbyTitle': '附近景点',
    'guide.nearbyDesc': '结合当前位置，为你推荐周边热门景点与服务点位。',
    'guide.voiceTitle': '语音讲解',
    'guide.voiceDesc': '点击景点即可进入语音讲解或跳转 AI 数字人问答。',
    'guide.locationTitle': '定位辅助',
    'guide.locationDesc': 'GPS 异常时可手动选择景点位置，继续完成导览。',
    'guide.routeSmartTitle': '智能路线推荐',
    'guide.routeSmartDesc': '根据天气、游览时长和游客兴趣，为你推荐更合适的灵山游览路线。',
    'guide.routeTag': '路线推荐',
    'guide.routeDayTitle': '一日深度游',
    'guide.routeNatureTitle': '自然风光路线',
    'guide.routeHalfDesc': '经典半日游路线，涵盖灵山主要景点，适合首次游览游客。',
    'guide.routeDayDesc': '一日深度游路线，全面体验灵山景区文化与自然风光。',
    'guide.routeFamilyDesc': '亲子轻松游路线，节奏舒缓，适合家庭出行。',
    'guide.routeCultureDesc': '文化深度游路线，聚焦佛教文化与历史遗迹。',
    'guide.routeNatureDesc': '自然风光路线，欣赏灵山秀美的山水景观。',
    'profile.title': '我的',
    'profile.guestTitle': '游客',
    'profile.guestSub': '登录后享受完整服务与历史记录',
    'profile.memberDesc': '已开通景区导览、收藏、历史问答等个人服务',
    'profile.serviceTitle': '个人服务',
    'profile.serviceDesc': '收藏、记录、反馈与系统设置集中管理',
    'profile.faq': '常见问题',
    'profile.favorites': '我的收藏',
    'profile.orders': '我的订单',
    'profile.history': '历史会话',
    'profile.qa': 'AI 对话',
    'profile.feedback': '我的反馈',
    'profile.settings': '设置',
    'profile.about': '关于系统',
    'profile.loginPrompt': '去登录',
    'profile.logout': '退出登录',
    'aiChat.title': 'AI 智能导游',
    'aiChat.back': '返回',
    'aiChat.topTag': 'AI 数字人对话',
    'aiChat.voiceEntry': '语音回答入口',
    'aiChat.syncStatus': '表情口型同步展示',
    'aiChat.thinking': '思考中...',
    'aiChat.listening': '正在聆听...',
    'aiChat.tapToSpeak': '点击语音输入',
    'aiChat.digitalIntro': '你好！我是小灵，你的灵山景区 AI 导览助手。可以为你讲解景点、推荐路线并提供游览建议。',
    'voice.recording': '正在聆听...',
    'voice.cancel': '松开取消',
    'voice.recognizing': '识别中...',
    'voice.error': '识别失败，请重试',
    'voice.holdToSpeak': '按住 说话',
    'voice.releaseToSend': '松开发送',
    'voice.permissionDenied': '请在设置中开启麦克风权限',
    'voice.micBusy': '麦克风被占用，请稍后再试',
    'voice.micUnavailable': '麦克风不可用',
    'voice.slideUpCancel': '↑ 上滑取消',
    'voice.releaseCancel': '松开取消',
  },
  'en-US': {
    'app.title': 'Lingshan Smart Tour AI Guide',
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
    'register.title': 'Begin Your Lingshan Journey',
    'register.subtitle': 'Get your own AI guide, route recommendations & scenic spot introductions',
    'register.button': 'Sign Up',
    'register.loading': 'Signing up...',
    'register.loginHint': 'Already have an account?',
    'register.loginLink': 'Sign in',
    'register.featureNote': 'Access AI Q&A, voice guide, and personalized route suggestions after registration',
    'register.welcomeTitle': 'Welcome',
    'register.welcomeSubtitle2': 'Create an account to start',
    'register.phoneLabel': 'Phone Number',
    'register.phonePlaceholder': 'Enter phone number',
    'register.smsCodeLabel': 'SMS Code',
    'register.smsCodePlaceholder': 'Enter SMS code',
    'register.getSmsCode': 'Get Code',
    'register.smsRetry': 's to retry',
    'register.confirmPasswordLabel': 'Confirm Password',
    'register.confirmPasswordPlaceholder': 'Re-enter password',
    'register.passwordMismatch': 'Passwords do not match',
    'register.agreePrefix': 'I agree to the',
    'register.terms': 'Terms',
    'register.and': 'and',
    'register.privacy': 'Privacy Policy',
    'register.agreementRequired': 'Please agree to the Terms and Privacy Policy',
    'register.otherLoginMethods': 'Other sign up/in methods',
    'register.wechat': 'WeChat',
    'register.qq': 'QQ',
    'register.thirdPartyWechatHint': 'WeChat login is coming soon',
    'register.thirdPartyQQHint': 'QQ login is coming soon',
    'register.smsNotAvailable': 'SMS verification is coming soon',
    'login.title': 'Login',
    'login.subtitle': 'Sign in to use the AI scenic assistant',
    'login.usernamePlaceholder': 'Enter your username',
    'login.passwordPlaceholder': 'Enter your password',
    'login.button': 'Sign In',
    'login.loading': 'Signing in...',
    'login.success': 'Login successful, start asking',
    'login.invalid': 'Invalid account or password, please try again',
    'login.serverError': 'Login failed, please try again later',
    'login.registerHint': 'Need an account?',
    'login.registerLink': 'Register',
    'login.chatLink': 'Open AI chat',
    'login.guestEntry': 'Visitor Experience Mode',
    'login.welcomeBack': 'Welcome Back',
    'login.welcomeBackSub': 'Please log in to continue',
    'login.phoneLabel': 'Phone/Account',
    'login.phonePlaceholder': 'Enter phone or account',
    'login.phoneRequired': 'Phone or account is required',
    'login.phoneInvalid': 'Please enter a valid phone number',
    'login.forgotPassword': 'Forgot password?',
    'login.smsLoginTab': 'SMS Login',
    'login.passwordLoginTab': 'Password',
    'login.smsCodeLabel': 'SMS Code',
    'login.smsCodePlaceholder': 'Enter SMS code',
    'login.getSmsCode': 'Get Code',
    'login.smsNotAvailable': 'SMS login is coming soon',
    'login.brandTitle': 'Lingshan Smart Tour',
    'login.brandSubtitle': 'Mountains and waters have voices, culture has answers — let AI guide you through Lingshan',
    'login.routeTitle': 'Recommended Route Today',
    'login.routeCard': 'Entrance → Jiulong Guan Yu → Lingshan Buddha → Fan Gong → Wuyin Altar',
    'login.routeDesc': 'Classic half-day tour · Best for first-time visitors · 3-4 hours',
    'login.welcome': 'Welcome to Lingshan Smart Tour',
    'login.welcomeSubtitle': 'Sign in for AI Q&A, voice guide & personalized route recommendations',
    'forgot.title': 'Forgot Password',
    'forgot.subtitle': 'Enter your phone number to reset',
    'forgot.phoneLabel': 'Phone Number',
    'forgot.phonePlaceholder': 'Enter registered phone',
    'forgot.smsCodeLabel': 'SMS Code',
    'forgot.smsCodePlaceholder': 'Enter SMS code',
    'forgot.getSmsCode': 'Get Code',
    'forgot.smsRetry': 's to retry',
    'forgot.newPasswordLabel': 'New Password',
    'forgot.newPasswordPlaceholder': 'Enter new password',
    'forgot.confirmPasswordLabel': 'Confirm Password',
    'forgot.confirmPasswordPlaceholder': 'Re-enter new password',
    'forgot.passwordMismatch': 'Passwords do not match',
    'forgot.button': 'Reset Password',
    'forgot.loading': 'Resetting...',
    'forgot.success': 'Password reset successful, please log in again',
    'forgot.backToLogin': 'Back to login',
    'forgot.smsNotAvailable': 'SMS verification is coming soon',
    'chat.title': 'Lingshan AI Guide · Xiao Ling',
    'chat.subtitle': 'I can tell you about Lingshan culture, recommend routes, and answer questions',
    'chat.inputPlaceholder': 'Ask me about Lingshan, e.g. "Plan a half-day tour for me"',
    'chat.empty': 'Hi, I am Xiao Ling, your Lingshan AI guide. You can ask me about scenic spots, hours, routes, tickets, and more.',
    'chat.send': 'Send',
    'chat.stop': 'Stop',
    'chat.clear': 'Clear chat',
    'chat.loading': 'AI is thinking...',
    'chat.aiLoading': 'Xiao Ling is searching the knowledge base...',
    'chat.loginNotice': 'Sign in to unlock the full AI chat experience',
    'chat.loggedInAs': 'Signed in as',
    'chat.goLogin': 'Go to login',
    'chat.logout': 'Sign out',
    'chat.reask': 'Ask again',
    'chat.quick.open': 'Is it open today?',
    'chat.quick.route': 'Plan a 2-hour route for me',
    'chat.quick.spots': 'Any stories about the Grand Buddha?',
    'chat.quick.ticket': 'When does Jiulong Guan Yu start?',
    'chat.error.empty': 'Please enter a question',
    'chat.error.loginRequired': 'Please log in first',
    'chat.error.failed': 'Request failed, please try again later',
    'chat.stopped': 'The current request was stopped',
    'chat.digitalName': 'Xiao Ling',
    'chat.digitalStatus': 'Guiding you through Lingshan',
    'chat.voiceOn': 'Voice On',
    'chat.voiceOff': 'Stop',
    'chat.location': 'Location',
    'chat.voiceInput': 'Voice Input',
    'chat.onlineStatus': 'AI Guide Online',
    'chat.voiceStatus': 'Voice Q&A Supported',
    'chat.kbStatus': 'Powered by Scenic KB',
    'chat.scenicToday': "Today's Guide",
    'chat.scenicOpen': 'Status: Subject to park notice',
    'chat.scenicRoute': 'Route: Classic Half-Day Tour',
    'chat.scenicCrowd': 'For: First-time, family, cultural visitors',
    'chat.scenicHotSpots': 'Hot Spots',
    'chat.scenicRoutes': 'Recommended Routes',
    'chat.scenicLocation': 'Location Assist',
    'chat.scenicLocationHint': 'If GPS is weak, manually select your location.',
    'chat.routeHalf': 'Classic Half-Day',
    'chat.routeCulture': 'Cultural In-Depth',
    'chat.routeFamily': 'Family Fun',
    'chat.routeTime': 'Duration',
    'chat.routeCrowd': 'Suitable for',
    'chat.routeReason': 'Why we recommend',
    'chat.routeSteps': 'Route',
    'chat.spotBuddha': 'Lingshan Buddha',
    'chat.spotJiulong': 'Jiulong Guan Yu',
    'chat.spotFangong': 'Fan Gong Palace',
    'chat.spotWuyin': 'Wuyin Altar',
    'chat.locEntrance': 'Entrance Plaza',
    'chat.locJiulong': 'Jiulong Guan Yu',
    'chat.locBuddha': 'Lingshan Buddha',
    'chat.locFangong': 'Fan Gong Palace',
    'chat.scenicInfo': 'Scenic Info',
    'drawer.close': 'Close',
    'toast.success': 'Registration succeeded',
    'toast.badRequest': 'Invalid request parameters',
    'toast.conflict': 'This username already exists',
    'toast.serverError': 'Server error, please try again later',
    'toast.networkError': 'Network request failed, please check your connection',
    'toast.unknown': 'Unknown error, please try again later',
    'success.redirect': 'Registration succeeded, redirecting to login',
    'home.welcome': 'Welcome to Lingshan',
    'home.weatherTitle': 'Wuxi Lingshan',
    'home.weatherAdvice': 'Great for sightseeing. Please use sun protection.',
    'home.weatherTag': 'Today',
    'home.aiEntryTitle': 'I am your Lingshan AI Guide',
    'home.aiEntrySub': 'Tap to chat with me',
    'home.aiEntryNote': 'Support scenic explanations, route recommendations, voice Q&A, and visitor services.',
    'home.aiEntryAction': 'Open AI Guide',
    'home.inputPlaceholder': 'Ask Lingshan AI Guide...',
    'home.services.spots': 'Scenic Spots',
    'home.services.guide': 'Smart Guide',
    'home.services.routes': 'Routes',
    'home.services.feedback': 'Feedback',
    'home.services.spotsDesc': 'Explore scenic spot details and stories',
    'home.services.guideDesc': 'Check the map, nearby spots, and current location',
    'home.services.routesDesc': 'Browse half-day, full-day, and family routes',
    'home.services.feedbackDesc': 'Open feedback and personal services',
    'nav.home': 'Home',
    'nav.guide': 'Guide',
    'nav.aiGuide': 'AI Guide',
    'nav.profile': 'Me',
    'guide.pageTitle': 'Scenic Guide & Route Planner',
    'guide.pageDesc': 'A mobile guide page that combines map guidance, scenic spots, location, and route planning.',
    'guide.tabMap': 'Scenic Map',
    'guide.tabRoutes': 'Routes',
    'guide.mapCardTitle': 'Scenic Map Guide',
    'guide.mapCardDesc': 'View scenic points, your location, and nearby services, then jump into voice guidance.',
    'guide.mapHint': 'Supports scenic browsing, current location lookup, and manual spot selection.',
    'guide.scenicTitle': 'Lingshan Scenic Guide',
    'guide.scenicDesc': 'Lingshan is the permanent site of the World Buddhist Forum, featuring the 88m Grand Buddha, Fan Gong Palace, Jiulong Guan Yu, and more. Recommended visit: 4-6 hours.',
    'guide.nearbyTitle': 'Nearby Spots',
    'guide.nearbyDesc': 'Recommend popular nearby attractions and service points based on your location.',
    'guide.voiceTitle': 'Voice Guide',
    'guide.voiceDesc': 'Tap a spot to start voice narration or jump into AI guide Q&A.',
    'guide.locationTitle': 'Location Assist',
    'guide.locationDesc': 'If GPS fails, manually choose your spot and continue the guide.',
    'guide.routeSmartTitle': 'Smart Route Recommendations',
    'guide.routeSmartDesc': 'Recommend better routes based on weather, available time, and traveler interests.',
    'guide.routeTag': 'Recommended',
    'guide.routeDayTitle': 'Full-Day Immersion',
    'guide.routeNatureTitle': 'Nature Route',
    'guide.routeHalfDesc': 'Classic half-day route covering main attractions, ideal for first-time visitors.',
    'guide.routeDayDesc': 'Full-day immersive route to experience Lingshan culture and nature.',
    'guide.routeFamilyDesc': 'Family-friendly route with a relaxed pace.',
    'guide.routeCultureDesc': 'Cultural deep-dive route focused on Buddhist heritage.',
    'guide.routeNatureDesc': 'Nature route showcasing Lingshan scenic landscapes.',
    'profile.title': 'Me',
    'profile.guestTitle': 'Visitor',
    'profile.guestSub': 'Sign in for full services and history',
    'profile.memberDesc': 'Guidance, favorites, and Q&A history are available in your account.',
    'profile.serviceTitle': 'Personal Services',
    'profile.serviceDesc': 'Manage favorites, history, feedback, and settings in one place.',
    'profile.faq': 'FAQ',
    'profile.favorites': 'My Favorites',
    'profile.orders': 'My Orders',
    'profile.history': 'Browsing History',
    'profile.qa': 'Q&A History',
    'profile.feedback': 'My Feedback',
    'profile.settings': 'Settings',
    'profile.about': 'About',
    'profile.loginPrompt': 'Sign in',
    'profile.logout': 'Sign out',
    'aiChat.title': 'AI Smart Guide',
    'aiChat.back': 'Back',
    'aiChat.topTag': 'AI Digital Human',
    'aiChat.voiceEntry': 'Voice answer entry',
    'aiChat.syncStatus': 'Expression & lip-sync display',
    'aiChat.thinking': 'Thinking...',
    'aiChat.listening': 'Listening...',
    'aiChat.tapToSpeak': 'Tap to speak',
    'aiChat.digitalIntro': 'Hi! I\'m Xiao Ling, your Lingshan AI guide. I can explain scenic spots, recommend routes, and offer travel suggestions.',
    'voice.recording': 'Listening...',
    'voice.cancel': 'Release to cancel',
    'voice.recognizing': 'Recognizing...',
    'voice.error': 'Recognition failed, please retry',
    'voice.holdToSpeak': 'Hold to speak',
    'voice.releaseToSend': 'Release to send',
    'voice.permissionDenied': 'Please enable microphone in settings',
    'voice.micBusy': 'Microphone is busy, please try later',
    'voice.micUnavailable': 'Microphone unavailable',
    'voice.slideUpCancel': '↑ Slide up to cancel',
    'voice.releaseCancel': 'Release to cancel',
  },
};

export function getLocale(): Locale {
  return navigator.language === 'en-US' ? 'en-US' : 'zh-CN';
}

export function t(key: MessageKey, locale = getLocale()): string {
  return messages[locale][key];
}
