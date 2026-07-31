/**
 * 固定选项常量
 * 所有页面的下拉选择、筛选器等统一引用此文件
 */

/** 验证码类型 */
export const codeTypes = [
  { label: '注册', value: 'register' },
  { label: '登录', value: 'login' },
] as const;

/** 登录方式 */
export const loginTypes = [
  { label: '密码登录', value: 'password' },
  { label: '验证码登录', value: 'code' },
] as const;

/** 兴趣路线 */
export const interests = [
  { label: '对历史文化感兴趣', value: '历史' },
  { label: '喜欢自然风光摄影', value: '自然' },
  { label: '亲子家庭出游', value: '亲子' },
  { label: '时间有限快速游', value: '入门' },
] as const;

/** 游览时长 */
export const routeHours = [
  { label: '2小时', value: 2 },
  { label: '3小时', value: 3 },
  { label: '4小时', value: 4 },
  { label: '5小时', value: 5 },
  { label: '6小时', value: 6 },
] as const;

/** 游览难度 */
export const routeDifficulties = [
  { label: '入门', value: '入门' },
  { label: '轻松', value: '轻松' },
  { label: '普通', value: '普通' },
  { label: '深度', value: '深度' },
] as const;

/** 反馈类型 */
export const feedbackTypes = [
  { label: '景点服务', value: '景点服务' },
  { label: '餐饮服务', value: '餐饮服务' },
  { label: '环境卫生', value: '环境卫生' },
  { label: '工作人员', value: '工作人员' },
  { label: '票务服务', value: '票务服务' },
  { label: '演出体验', value: '演出体验' },
  { label: '其他', value: '其他' },
] as const;

/** 反馈评分 */
export const ratings = [
  { label: '非常差', value: 1 },
  { label: '较差', value: 2 },
  { label: '一般', value: 3 },
  { label: '较好', value: 4 },
  { label: '非常好', value: 5 },
] as const;

/** FAQ 分类 */
export const faqCategories = [
  { label: '全部', value: null },
  { label: '开放时间', value: '开放时间' },
  { label: '票价', value: '票价' },
  { label: '演出', value: '演出' },
  { label: '路线推荐', value: '路线推荐' },
  { label: '景点介绍', value: '景点介绍' },
  { label: '文化背景', value: '文化背景' },
  { label: '餐饮', value: '餐饮' },
  { label: '住宿', value: '住宿' },
  { label: '交通', value: '交通' },
  { label: '实用贴士', value: '实用贴士' },
  { label: '其他', value: '其他' },
] as const;
