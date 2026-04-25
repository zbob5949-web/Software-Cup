A5赛题要求网址：https://www.cnsoftbei.com/content-3-1245-1.html


软件工程规范：
底层开发语言统一为python
分支 命名规范：feature/backend（表明工作性质）-具体功能
文件名命名规范：backend-具体功能
函数命名：大驼峰命名法
变量命名：小驼峰命名法







服务器公网ip:8.136.141.135
服务器登录网址：https://swasnext.console.aliyun.com/servers/cn-hangzhou
服务器登录账号：nick8806553726
密码：@Zjn200627
在左侧就能看到：
<img width="618" height="552" alt="{4D504E75-019F-48D5-89CA-6AFFB140591A}" src="https://github.com/user-attachments/assets/3b3f737c-a387-4788-a691-db0120266e4f" />


后端注意：先在电脑上用主机ip写接口--例如：@app.post("/api/save")没有添加ip默认主机IP，接口写完用apifox或者postman测试 通过后新建功能分支commit加push到github 
用CROS开启跨域 允许所有前端访问，传完接口到服务器后必须写 0.0.0.0公网开放启动命令便于前端请求


前端注意：基本不用管服务器 只需要记住服务器公网ip即可,如果需要使用放在服务器里的接口就登陆后在服务器的命令行里输入：uvicorn main:app --host 0.0.0.0 --port 8000，先把服务器以谁都可以访问的形式打开，然后再用自己的前端程序访问接口，退出账号服务器会自动关闭（访问接口时使用http://8.136.141.135:8000/api/post，8000为fastapi端口）


1.分工



姚志颖：前端界面

技能需求：1.HTML+CSS+JavaScript

&#x09;	2.vue3写框架

&#x09;	3.axios

&#x09;	4.接口联调

&#x09;	5.Echarts

&#x09;	6.视频流控制



陶帅宇：后端

&#x09;	1.数据库（问答统计）

&#x09;	2.项目工程化

&#x09;	3.ai模块接口化

&#x09;	4.Fast api(快速写后端接口)

&#x09;	5.

&#x09;	6.





张居念：ai加全栈
1.api调用（语音识别、数字人）

&#x09;	2.RAG流程及逻辑

&#x09;	3.多模态基础

&#x09;	4.简单数据处理

&#x09;	5.部署运行

&#x09;	6.git管理

&#x09;	7，简单运维、测试


请求方式：POST&GET

传递格式：josn



景区资料转为纯文本，分类





接口：
1.问答接口
2.语音接口
3.知识库接口
4.数据统计接口


超过100MB的数据集/预训练模型 下载链接：

分支 命名规范：feature/backend（表明工作性质）-具体功能
文件名命名规范：backend-具体功能
函数命名：大驼峰命名法
变量命名：小驼峰命名法

