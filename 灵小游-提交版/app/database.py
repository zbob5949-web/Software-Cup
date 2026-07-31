# -*- coding: utf-8 -*-
"""
database.py
SQLite 本地数据库（零依赖，替代 MySQL）
接口完全兼容旧代码：其他模块无需修改，继续用 get_db_connection() / %s 占位符。
"""
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lingshan.db"


class _CompatCursor:
    """sqlite3 游标包装：自动转换 MySQL 语法 → SQLite 语法，返回字典格式。"""

    def __init__(self, raw_cursor: sqlite3.Cursor):
        self._cur = raw_cursor

    @staticmethod
    def _translate(sql: str) -> str:
        # 基础替换：占位符
        sql = sql.replace("%s", "?")

        # 1. DATE_SUB 复合表达式（必须在 NOW()/CURDATE() 简单替换之前处理）
        #    DATE_SUB(NOW(), INTERVAL ? DAY) → datetime('now', '-' || ? || ' days')
        #    同时支持参数占位 (?) 和硬编码数字
        sql = re.sub(
            r"DATE_SUB\(NOW\(\),\s*INTERVAL\s+(\?|\d+)\s+DAY\)",
            r"datetime('now', '-' || \1 || ' days')",
            sql,
        )
        # DATE_SUB(CURDATE(), INTERVAL ? DAY) → date('now', '-' || ? || ' days')
        sql = re.sub(
            r"DATE_SUB\(CURDATE\(\),\s*INTERVAL\s+(\?|\d+)\s+DAY\)",
            r"date('now', '-' || \1 || ' days')",
            sql,
        )

        # 2. 裸 NOW() / CURDATE()（在 DATE_SUB 之后处理）
        sql = sql.replace("NOW()", "datetime('now')")
        sql = sql.replace("CURDATE()", "date('now')")

        # 3. DATE(expr) → date(expr)  — SQLite date() 函数
        sql = re.sub(r"\bDATE\(", "date(", sql)

        # 4. YEARWEEK(col, 1) → cast(strftime('%Y%W', col) as integer)
        sql = re.sub(
            r"YEARWEEK\(([^,]+),\s*1\)",
            r"cast(strftime('%Y%W', \1) as integer)",
            sql,
        )

        # 5. CONCAT(a, b, ...) → (a || b || ...)
        sql = re.sub(
            r"CONCAT\(([^)]+)\)",
            lambda m: "(" + " || ".join(
                part.strip() for part in m.group(1).split(",")
            ) + ")",
            sql,
        )

        # 6. IFNULL(a, b) → coalesce(a, b)
        sql = re.sub(r"\bIFNULL\(", "coalesce(", sql)

        # 7. FOR UPDATE → 移除（SQLite 不支持 SELECT ... FOR UPDATE，在事务中自动处理）
        sql = re.sub(r"\s+FOR\s+UPDATE\b", "", sql, flags=re.IGNORECASE)

        return sql

    def execute(self, sql: str, params=None):
        if params is None:
            return self._cur.execute(self._translate(sql))
        return self._cur.execute(self._translate(sql), params)

    def executemany(self, sql: str, seq):
        return self._cur.executemany(self._translate(sql), seq)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description] if self._cur.description else []
        return dict(zip(cols, row))

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cur.description] if self._cur.description else []
        return [dict(zip(cols, r)) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    def close(self):
        self._cur.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _CompatConnection:
    """sqlite3 连接包装。"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def cursor(self):
        return _CompatCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db_connection():
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return _CompatConnection(conn)
    except Exception as e:
        print(f"[数据库] 连接失败: {e}")
        return None


def init_database():
    conn = get_db_connection()
    if not conn:
        print("[数据库] 初始化失败")
        return
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(11) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL, role VARCHAR(20) DEFAULT 'user',
            is_active INTEGER DEFAULT 1, is_super_admin INTEGER DEFAULT 0,
            last_login_ip VARCHAR(64), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS verification_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(11) NOT NULL,
            code VARCHAR(4) NOT NULL, code_type VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS chat_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(15),
            session_id VARCHAR(64) NOT NULL, role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL, source VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(100) NOT NULL,
            category VARCHAR(50), description TEXT, open_time VARCHAR(100),
            duration VARCHAR(50), tips TEXT, sort_order INTEGER DEFAULT 0,
            image_url VARCHAR(255), is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(100) NOT NULL,
            duration VARCHAR(50), difficulty VARCHAR(20), description TEXT,
            spot_ids VARCHAR(255), hours_min INTEGER DEFAULT 0,
            hours_max INTEGER DEFAULT 24, is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(11),
            type VARCHAR(50) NOT NULL, rating INTEGER NOT NULL,
            content TEXT NOT NULL, status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(11) NOT NULL,
            spot_id INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (phone, spot_id))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS route_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(11) NOT NULL,
            route_id INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (phone, route_id))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS ticket_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone VARCHAR(11) NOT NULL,
            ticket_id INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (phone, ticket_id))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, spot_id INTEGER,
            name VARCHAR(100) NOT NULL, ticket_type VARCHAR(50) NOT NULL DEFAULT '门票',
            price REAL NOT NULL DEFAULT 0, stock INTEGER NOT NULL DEFAULT 0,
            valid_date DATE, status VARCHAR(20) NOT NULL DEFAULT 'on_sale',
            description TEXT, code VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS ticket_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_no VARCHAR(32) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL, ticket_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL, unit_price REAL NOT NULL,
            total_amount REAL NOT NULL, visitor_name VARCHAR(50) NOT NULL,
            visitor_phone VARCHAR(11) NOT NULL,
            order_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            remark VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question VARCHAR(255) NOT NULL,
            answer TEXT NOT NULL, category VARCHAR(50), keywords VARCHAR(255),
            sort_order INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS digital_human_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_key VARCHAR(80) NOT NULL DEFAULT 'live2d_haru',
            name VARCHAR(100) NOT NULL,
            voice_name VARCHAR(100) DEFAULT 'zh-CN-XiaoxiaoNeural',
            voice_style VARCHAR(100), appearance TEXT, clothing TEXT,
            cultural_style TEXT, keywords TEXT, is_active INTEGER DEFAULT 0,
            speed REAL DEFAULT 1.0, volume REAL DEFAULT 0.8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sentiment_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, period_start DATE NOT NULL,
            period_end DATE NOT NULL, source VARCHAR(50) NOT NULL, summary TEXT,
            positive_count INTEGER DEFAULT 0, neutral_count INTEGER DEFAULT 0,
            negative_count INTEGER DEFAULT 0, suggestions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
        print("[数据库] 建表完成")

        # 兼容迁移：为旧版 digital_human_configs 表添加 speed/volume 列
        _migrate_digital_human_configs(cur)

        _seed_data(cur)
        _seed_tickets(cur)
        try:
            _seed_ticket_orders(cur)
        except Exception as e:
            import traceback
            print(f"[数据库] 订单种子数据跳过: {type(e).__name__}: {e}")
            traceback.print_exc()
        _seed_digital_human_configs(cur)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[数据库] 建表失败: {e}")
    finally:
        conn.close()


def _migrate_digital_human_configs(cur):
    """为旧版数据库添加 speed/volume 列（兼容已有安装）"""
    try:
        cur.execute("SELECT speed FROM digital_human_configs LIMIT 0")
    except Exception:
        try:
            cur.execute("ALTER TABLE digital_human_configs ADD COLUMN speed REAL DEFAULT 1.0")
            cur.execute("ALTER TABLE digital_human_configs ADD COLUMN volume REAL DEFAULT 0.8")
            print("[数据库] 已为 digital_human_configs 添加 speed/volume 列")
        except Exception:
            pass


def _seed_tickets(cur):
    products = [
        ("灵山胜境成人票", "成人票", 210, 300, "18周岁以上成年人，含灵山胜境主景区参观"),
        ("灵山胜境半价票", "半价票", 105, 300, "6-18周岁未成年人、全日制本科及以下学生、60-69周岁老人"),
        ("灵山胜境免票", "免票", 0, 300, "6周岁以下或1.4米以下儿童、70周岁以上老人、现役军人、残疾人"),
        ("门票 + 观光车联票", "联票", 225, 300, "门票与景区观光车无限次乘坐，更划算"),
        ("观光车单独购票", "观光车票", 40, 300, "景区内交通，适合体力有限的游客"),
    ]
    try:
        cur.execute("SELECT COUNT(*) AS cnt FROM tickets")
        if cur.fetchone()["cnt"] == 0:
            cur.executemany(
                "INSERT INTO tickets (name, ticket_type, price, stock, status, description) VALUES (%s, %s, %s, %s, 'on_sale', %s)",
                products)
        services = [
            ("素面", "餐食服务", 35, 300, "景区内清淡素食"),
            ("素斋", "餐食服务", 50, 300, "佛门素斋套餐"),
            ("导游服务", "导游服务", 300, 100, "景区历史文化深度讲解服务"),
        ]
        for service in services:
            cur.execute("SELECT id FROM tickets WHERE name = %s LIMIT 1", (service[0],))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO tickets (name, ticket_type, price, stock, status, description) VALUES (%s, %s, %s, %s, 'on_sale', %s)",
                    service)
    except Exception as exc:
        print(f"[数据库] 票种初始化失败: {exc}")


def _seed_ticket_orders(cur):
    """种子订单数据，用于消费分析维度展示"""
    import random
    from datetime import datetime, timedelta

    cur.execute("SELECT COUNT(*) AS cnt FROM ticket_orders")
    if cur.fetchone()["cnt"] > 0:
        return

    cur.execute("SELECT id, price FROM tickets")
    tickets = cur.fetchall()
    if not tickets:
        return

    now = datetime.now()
    for i in range(20):
        t = random.choice(tickets)
        tid = t["id"]
        price = t["price"] or 50
        qty = random.randint(1, 3)
        days_ago = random.randint(0, 20)
        dt = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO ticket_orders (order_no, user_id, ticket_id, quantity, unit_price, total_amount, visitor_name, visitor_phone, order_status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                f"ORD{now.strftime('%Y%m%d')}{i:04d}",
                random.choice([1, 2, 3, 6]),
                tid, qty, price, price * qty,
                f"游客{i}", f"1380000{i:04d}",
                random.choice(["paid", "paid", "paid", "paid", "completed", "pending"]),
                dt,
            ),
        )
    print(f"[数据库] 订单样本数据 20 条")


def _seed_digital_human_configs(cur):
    profiles = [
        ("live2d_haru", "Haru 灵小游", "zh-CN-XiaoyiNeural", "少女/清亮", "当前主形象", "樱色景区导览制服", "亲和、轻盈", "Haru,少女,亲和", 1),
        ("live2d_hiyori", "Hiyori 灵小游", "zh-CN-XiaoxiaoNeural", "清新/温柔", "Hiyori Live2D形象", "青绿色自然风导览服", "清新、温柔", "Hiyori,清新,温柔", 0),
        ("live2d_mao", "Mao 灵小游", "zh-CN-XiaoyiNeural", "活泼/元气", "Mao Live2D形象", "明快活泼的景区导览服", "元气、活泼", "Mao,活泼,元气", 0),
    ]
    try:
        cur.execute("DELETE FROM digital_human_configs WHERE model_key NOT IN ('live2d_haru', 'live2d_hiyori', 'live2d_mao')")
        for p in profiles:
            cur.execute("SELECT id FROM digital_human_configs WHERE model_key = %s LIMIT 1", (p[0],))
            if not cur.fetchone():
                cur.execute("INSERT INTO digital_human_configs (model_key, name, voice_name, voice_style, appearance, clothing, cultural_style, keywords, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", p)
        cur.execute("UPDATE digital_human_configs SET is_active = 0 WHERE model_key <> 'live2d_haru' AND is_active = 1")
        cur.execute("SELECT COUNT(*) AS cnt FROM digital_human_configs WHERE is_active = 1")
        if cur.fetchone()["cnt"] == 0:
            cur.execute("UPDATE digital_human_configs SET is_active = 1 WHERE model_key = 'live2d_haru'")
        print("[数据库] 三个 Live2D 数字人配置已就绪")
    except Exception as exc:
        print(f"[数据库] Live2D 配置写入失败: {exc}")


def _seed_data(cur):
    try:
        # 默认管理员
        cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE phone = 'admin'")
        if cur.fetchone()['cnt'] == 0:
            from app.core.security import hash_password
            cur.execute("INSERT INTO users (phone, password, role, is_active, is_super_admin) VALUES (%s, %s, %s, 1, 1)",
                        ('admin', hash_password('admin123'), 'admin'))
            print("[数据库] 默认管理员已创建: admin / admin123")

        # 演示用户（用于管理后台展示）
        cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE phone = 'user'")
        if cur.fetchone()['cnt'] == 0:
            from app.core.security import hash_password
            demo_users = [
                ('user', hash_password('user123'), 'user', 1, 0),
                ('13900001111', hash_password('user123'), 'user', 1, 0),
                ('13900002222', hash_password('user123'), 'user', 1, 0),
                ('13900003333', hash_password('user123'), 'user', 0, 0),
                ('13900005555', hash_password('user123'), 'admin', 1, 0),
            ]
            for u in demo_users:
                cur.execute(
                    "INSERT INTO users (phone, password, role, is_active, is_super_admin) VALUES (%s, %s, %s, %s, %s)",
                    u,
                )
            print(f"[数据库] 演示用户 {len(demo_users)} 个已创建")

        # 景点 (23条)
        cur.execute("SELECT COUNT(*) AS cnt FROM spots")
        if cur.fetchone()['cnt'] == 0:
            spots = [
                ("灵山大照壁", "建筑", "景区入口标志性建筑，被誉为'华夏第一壁'。长39.8米，高7米，采用优质青石雕刻而成。正面赵朴初先生亲笔题写鎏金'灵山胜境'四字，背面刻有《小灵山》诗刻。", "全天开放", "15分钟", "进园第一处打卡点，正面拍摄鎏金大字最佳，与太湖背景同框留念。", 1, None),
                ("五明桥", "建筑", "横跨香水海的五座汉白玉石拱桥，代表佛教五种核心智慧：声明（语言学）、因明（逻辑学）、内明（哲学）、医方明（医学）、工巧明（工艺学），寓意过桥即开启智慧。", "全天开放", "10分钟", "漫步过桥时可对应五种智慧，拍摄桥与水面倒影。", 2, None),
                ("佛足坛", "建筑", "复刻佛祖释迦牟尼真身脚印，巨型青铜佛足印一对，每只长1.2米、宽0.6米。足心刻有千辐轮相、宝瓶鱼纹等32种吉祥图案，象征'佛足所至，佛光普照'。", "全天开放", "10分钟", "亲手触摸足心32种吉祥图案寄托祈福。", 3, None),
                ("五智门", "建筑", "核心景区门户，高16.8米、宽35米，五门六柱汉白玉石牌坊。五门象征五方五佛，六柱代表'六度波罗蜜'。穿过此门，从'凡俗之境'踏入'禅意圣地'。", "全天开放", "10分钟", "穿门祈福，夜间有灯光点缀。", 4, None),
                ("菩提大道", "建筑", "长约250米、宽约10米的朝圣步道，两侧对称种植近百棵印度引进菩提树，形成天然禅意拱廊，象征佛陀菩提树下悟道成佛。", "全天开放", "10分钟", "春季菩提花开绝美；可捡拾菩提叶做书签。", 5, None),
                ("九龙灌浴", "演出", "灵山胜境最具标志性动态景观，总高27.2米。核心为7.2米高鎏金太子佛。依据《本行经》打造，再现'花开见佛，九龙沐浴'祥瑞景象。演出时九龙喷水高达数十米。", "平日10:00/11:30/13:30/15:00", "20分钟", "提前10分钟占位，演出后可接取圣水祈福。", 6, None),
                ("降魔浮雕", "建筑", "长26米、高4.6米巨型花岗岩石雕。中央佛陀端坐菩提树下，两侧魔王波旬率魔女、魔兵诱惑威胁。传递'坚守本心、终能成道'的禅理。", "全天开放", "15分钟", "佛教文化核心科普点，了解佛陀'八相成道'。", 7, None),
                ("阿育王柱", "建筑", "通高16.9米，重180吨，整块花岗岩雕刻。柱头四头狮子朝向四方，象征佛法向世界传播。阿育王统一印度后笃信佛教，是佛教东传的重要象征。", "全天开放", "10分钟", "四狮柱头细节精美，与灵山大佛同一中轴线。", 8, None),
                ("百子戏弥勒", "建筑", "高3米、宽7.8米、重9吨青铜群雕。弥勒佛卧姿袒胸露腹笑容可掬，百名孩童形态各异，寓意'多子多福、家庭和睦'。", "全天开放", "15分钟", "触摸弥勒肚皮寓意'享一生福气'；亲子拍照热门。", 9, None),
                ("祥符禅寺", "建筑", "千年古刹，始建于唐贞观年间，玄奘弟子窥基大师开坛讲经。北宋赐额'祥符禅寺'。遗存：千年银杏、六角古井（茶圣陆羽品鉴）、江南第一钟（12.8吨）。", "全天开放", "30分钟", "可撞钟祈福；秋季银杏金黄绝美。", 10, None),
                ("灵山大佛", "佛像", "世界最高露天青铜释迦牟尼立像。通高88米，总高101.5米，耗铜725吨。1997年落成开光。右手施无畏印，左手施与愿印。216级登云道暗合108烦恼与108愿望。", "07:00-17:30", "40分钟", "抱佛脚祈福；登顶俯瞰太湖全景；夕阳下佛光普照最壮观。", 11, None),
                ("天下第一掌", "体验", "灵山大佛右手等比复制品，高11.7米、宽5.5米。摸掌祈福，寓意'沾福气、保平安'。与'抱佛脚'并称灵山两大祈福体验。", "07:00-17:30", "15分钟", "站在掌心仰拍大佛角度绝佳。", 12, None),
                ("佛教文化博览馆", "建筑", "设于灵山大佛三层座基内，10000平方米，免费开放。一层五方五佛与四大名山，二层世界佛教发展史，三层万佛殿9999尊小佛像'万佛朝宗'。", "08:00-17:00", "40分钟", "免费讲解9:30/11:00/14:30/16:00。", 13, None),
                ("灵山梵宫", "建筑", "被誉为'东方卢浮宫'，72000平方米，鲁班奖。世界佛教论坛永久会址。三大核心：28米高纯金星空穹顶、《华藏世界》琉璃巨制、东阳木雕群。", "09:00-17:00", "60-90分钟", "《吉祥颂》10:35/11:30/14:00/16:00，凭门票免费。", 14, None),
                ("五印坛城", "建筑", "香水海中央独立圆岛，五层藏式楼宇，'小布达拉宫'之称。'五印'代表五方五佛五种手印。108个转经筒，唐卡矿物颜料百年鲜艳。", "09:00-17:00", "40分钟", "转经筒祈福；登顶俯瞰全景；可预约藏香制作。", 15, None),
                ("曼飞龙塔", "建筑", "复刻西双版纳曼飞龙白塔，主塔高16.9米，九塔组合象征南传佛教九种智慧。与梵宫（汉传）、五印坛城（藏传）并列三大语系。", "全天开放", "20分钟", "九塔搭配香水海拍照绝美；夜间亮化别有韵味。", 16, None),
                ("无尽意斋", "建筑", "赵朴初先生北京故居复原四合院，2008年建成。分生平事迹厅、灵山渊源厅、书法作品厅。免费禅茶品鉴。", "09:00-17:00", "30分钟", "免费参观；禅茶免费品鉴；书法真迹禁止闪光灯。", 17, None),
                ("拈花广场", "建筑", "拈花湾入口核心，8000平方米。中央12米'拈花微笑'青铜鎏金雕塑。每日9:30禅意开园仪式。", "09:00-21:30", "15分钟", "与雕塑打卡合影；夜间18:00亮灯。", 18, None),
                ("梵天花海", "自然", "拈花湾最大自然景观区，30000平方米。四季有花：春格桑花、夏硫华菊、秋波斯菊。木质步道1500米，中央歇山顶凉亭。", "09:00-21:30", "30分钟", "四季拍摄花卉；禁止采摘；夏季注意防蚊。", 19, None),
                ("香月花街", "建筑", "拈花湾核心商业街，全长800米。禅意文创、非遗手作、特色餐饮、禅茶品鉴。夜间灯笼街巷氛围感十足。", "09:00-21:30", "60分钟", "夜间18:00亮灯；每日不定时禅意巡游。", 20, None),
                ("拈花堂", "建筑", "拈花湾静心场所，1200平方米。禅坐区、抄经区、禅茶区。每日禅意讲座10:30/15:30。抄经可带走。", "09:30-19:00", "40分钟", "保持安静，手机静音；禅坐抄经禅茶均免费。", 21, None),
                ("五灯湖", "自然", "拈花湾最大水景区，5000平方米。夜间《禅行》灯光秀19:00/20:00各一场，灯光投影搭配水雾如梦如幻。", "09:00-21:30", "30分钟", "夏季可赏荷花；夜间灯光秀提前占位。", 22, None),
                ("鹿鸣谷", "自然", "拈花湾西侧山林间，20000平方米，植被覆盖率90%以上。木质步道1.5公里，空气清新，适合静心漫步。", "随拈花湾开放", "30-40分钟", "雨天注意防滑；傍晚游览最佳。", 23, None),
            ]
            cur.executemany("INSERT INTO spots (name, category, description, open_time, duration, tips, sort_order, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", spots)
            print(f"[数据库] 景点数据 {len(spots)} 条")

        # 路线 (4条)
        cur.execute("SELECT COUNT(*) AS cnt FROM routes")
        if cur.fetchone()['cnt'] == 0:
            routes = [
                ("佛国入门精华游", "2-3小时", "入门", "适合时间有限初次访客。灵山大照壁→九龙灌浴→灵山大佛。建议10点入园赶九龙灌浴首场。", "1,6,11", 2, 3),
                ("亲子家庭轻松游", "4小时", "轻松", "适合带孩子的家庭。九龙灌浴→天下第一掌→百子戏弥勒→灵山梵宫→五印坛城。梵宫素斋50元/位。", "6,12,9,14,15", 3, 4),
                ("自然风光全景游", "5小时", "普通", "摄影与自然风光爱好者。佛足坛→九龙灌浴→菩提大道→灵山大佛→曼飞龙塔。下午入园拍太湖日落。", "3,6,5,11,16", 5, 5),
                ("历史文化深度游", "6小时", "深度", "历史文化爱好者。灵山大照壁→天下第一掌→祥符禅寺→灵山大佛→灵山梵宫→五印坛城。导游300元起。", "1,12,10,11,14,15", 6, 8),
            ]
            cur.executemany("INSERT INTO routes (name, duration, difficulty, description, spot_ids, hours_min, hours_max) VALUES (%s, %s, %s, %s, %s, %s, %s)", routes)
            print(f"[数据库] 路线数据 {len(routes)} 条")

        # FAQ (26条)
        cur.execute("SELECT COUNT(*) AS cnt FROM faqs")
        if cur.fetchone()['cnt'] == 0:
            faqs = [
                ("今天开放吗？", "灵山胜境每天正常开放，主要景区 **07:00-17:30**（最后入园17:00）。\n\n室内场馆：\n- 灵山梵宫、五印坛城、无尽意斋：**09:00-17:00**（冬季16:30）\n- 佛教文化博览馆：**08:00-17:00**（冬季16:30）\n- 拈花湾：**09:00-21:30**（冬季20:30）\n\n以景区当日公告为准。", "开放时间", "今天,开放,营业,开门", 1),
                ("梵宫几点开放？", "**灵山梵宫** 开放 **09:00-17:00**，冬季16:30闭馆。\n《吉祥颂》演出 **10:35/11:30/14:00/16:00**，凭大门票免费。建议提前30分钟排队。", "开放时间", "梵宫,开放时间,几点", 2),
                ("门票多少钱？", "灵山胜境门票：\n- **成人票：210元**（18周岁以上）\n- **半价票：105元**（6-18周岁/学生/60-69周岁老人）\n- **免票**：6周岁以下/70周岁以上/现役军人/残疾人\n- **联票：225元**（门票+观光车无限次）\n- 观光车单独：40元/人\n以景区官方价格为准。", "票价", "门票,价格,多少钱,票价", 3),
                ("有什么优惠政策吗？", "**半价票（105元）：** 6-18周岁、全日制学生（凭学生证）、60-69周岁老人\n**免票：** 6周岁以下/1.2米以下儿童、70周岁以上、现役军人、残疾人\n**最划算：联票225元** = 门票+观光车无限次", "票价", "优惠,半价,免票,学生", 4),
                ("观光车在哪里坐？多少钱？", "**价格：** 单独40元/人，联票225元更划算。\n**乘坐点：** 景区内多处站点，按指示牌找到。建议老人儿童购买联票。", "票价", "观光车,在哪,交通,坐车", 5),
                ("九龙灌浴几点有演出？", "平日：**10:00 / 11:30 / 13:30 / 15:00**，每场约15-20分钟。节假日加场（以广播为准）。提前10分钟到场，正面视角最佳。演出后接取圣水祈福。", "演出", "九龙灌浴,演出,几点,表演", 6),
                ("吉祥颂演出在哪里看？", "**《灵山吉祥颂》** 在 **灵山梵宫圣坛**。每日 **10:35/11:30/14:00/16:00** 共4场，每场20分钟。凭大门票免费！全球唯一大型旋转舞台+全息投影。提前30分钟到场。", "演出", "吉祥颂,梵宫,演出,在哪", 7),
                ("帮我规划2小时游览路线", "**佛国入门精华游（2-3小时）：**\n① 灵山大照壁（打卡）\n② 九龙灌浴（必看！接圣水）\n③ 灵山大佛（抱佛脚，俯瞰太湖）\n建议10点入园赶九龙灌浴首场。", "路线推荐", "2小时,入门,精华,路线", 8),
                ("帮我规划4小时游览路线", "**亲子家庭轻松游（4小时）：**\n① 九龙灌浴\n② 天下第一掌（摸掌祈福）\n③ 百子戏弥勒（亲子互动）\n④ 灵山梵宫（《吉祥颂》）\n⑤ 五印坛城（转经筒）\n建议9点前入园，梵宫素斋50元/位。", "路线推荐", "4小时,亲子,规划路线", 9),
                ("帮我规划5小时游览路线", "**自然风光全景游（5小时）：**\n① 佛足坛\n② 九龙灌浴（圣水+七彩佛光）\n③ 菩提大道（林荫风水格局）\n④ 灵山大佛（俯瞰太湖日落）\n⑤ 曼飞龙塔（南传建筑）\n推荐下午入园拍太湖日落。", "路线推荐", "5小时,自然,摄影,风光", 10),
                ("帮我规划6小时深度游", "**历史文化深度游（6小时）：**\n① 灵山大照壁（赵朴初书法）\n② 天下第一掌\n③ 祥符禅寺（千年古刹撞钟）\n④ 灵山大佛（五方五佛解析）\n⑤ 灵山梵宫（三大艺术核心）\n⑥ 五印坛城（藏传文化）\n建议预约导游300元起。", "路线推荐", "6小时,深度,历史,文化", 11),
                ("灵山大佛有什么故事？", "**灵山大佛** 世界最高露天青铜释迦牟尼立像，通高**88米**，总高101.5米，耗铜725吨，1997年落成。\n玄奘法师途经马山见'山形酷似印度灵鹫山'命名'小灵山'。赵朴初提出'五方五佛'格局。右手施无畏印，左手施与愿印。216级登云道：前108级烦恼尽除，后108级愿望圆满。", "景点介绍", "灵山大佛,故事,介绍,历史", 12),
                ("梵宫有什么看点？", "**灵山梵宫** '东方卢浮宫'，72000平方米，鲁班奖。\n三大核心：①28米高穹顶100公斤纯金绘148飞天 ②《华藏世界》琉璃巨制160块拼接 ③东阳木雕群金丝楠木。\n《灵山吉祥颂》每日4场，凭门票免费。", "景点介绍", "梵宫,看点,东方卢浮宫", 13),
                ("祥符禅寺有什么历史？", "**祥符禅寺** 千年古刹，唐贞观玄奘弟子窥基大师开创。北宋赐额'祥符禅寺'。\n三大遗存：千年银杏（秋季金黄）、六角古井（茶圣陆羽品鉴）、江南第一钟（12.8吨）。可撞钟祈福。", "景点介绍", "祥符禅寺,历史,千年古刹", 14),
                ("午餐吃什么？", "灵山餐饮以**佛门素斋**为特色：\n- 梵宫素斋自助（约50元/位）\n- 素面套餐（约35元/位）\n- 灵山精舍素斋\n- 拈花湾香月花街各式禅意餐饮\n无尽意斋、拈花堂提供免费禅茶。", "餐饮", "吃的,餐饮,素斋,素面,吃饭", 15),
                ("你是谁？", "我是 **灵山景区智能助手小贞** 🪷\n可以为您提供景点介绍、路线规划、门票信息、演出时间、餐饮住宿等咨询服务。请问您想了解什么？", "其他", "你是谁,小贞,介绍", 16),
            ]
            cur.executemany("INSERT INTO faqs (question, answer, category, keywords, sort_order) VALUES (%s, %s, %s, %s, %s)", faqs)
            print(f"[数据库] FAQ数据 {len(faqs)} 条")

        _seed_feedback_and_chat(cur)
        print("[数据库] 初始数据写入完成")
    except Exception as e:
        print(f"[数据库] 初始数据写入失败: {e}")


def _seed_feedback_and_chat(cur):
    """种子数据：用户感受报告所需的反馈记录与对话记录（用于演示）"""
    from datetime import datetime, timedelta
    import random

    # ---- 反馈数据 ----
    cur.execute("SELECT COUNT(*) AS cnt FROM feedbacks")
    if cur.fetchone()["cnt"] == 0:
        feedbacks = [
            # 正向反馈
            ("138****1234", "服务体验", 5, "数字人导游太方便了！语音问答反应快，讲解也很专业，带孩子来玩省心多了。", "reviewed"),
            ("139****5678", "景点评价", 5, "灵山大佛太震撼了！灵小游推荐的2小时精华路线特别合理，第一次来也不会迷路。", "reviewed"),
            ("136****9012", "服务体验", 4, "整体体验不错，数字人回答大部分问题都很快，就是偶尔网络不好会卡一下。", "reviewed"),
            ("137****3456", "餐饮服务", 5, "梵宫素斋真不错，灵小游推荐的那家素面馆位置很准，价格也实惠。", "reviewed"),
            ("135****7890", "路线推荐", 4, "亲子路线安排得很好，百子戏弥勒孩子玩得很开心，就是观光车排队久了点。", "reviewed"),
            ("133****2468", "景点评价", 5, "五印坛城的转经筒体验很棒，灵小游讲的藏传佛教知识通俗易懂，收获满满！", "reviewed"),
            ("132****1357", "服务体验", 5, "语音识别很准，我讲方言都能听懂，这个AI导游做得真不错👍", "reviewed"),
            ("131****8642", "演出体验", 4, "九龙灌浴演出很壮观，灵小游提前提醒我10点场，不然就错过了。好评！", "reviewed"),
            ("130****9753", "景点评价", 5, "夕阳下的灵山大佛太美了，灵小游推荐的拍摄角度绝了，朋友圈被赞爆！", "reviewed"),
            ("129****4680", "整体体验", 5, "第一次来灵山就遇到这么智能的导游，整个游览节奏都很舒服，强烈推荐！", "reviewed"),
            ("128****3579", "路线推荐", 4, "历史文化深度游路线设计得很专业，祥符禅寺的千年银杏美极了，值得慢慢逛。", "reviewed"),
            ("127****2468", "服务体验", 3, "功能还可以，但有时问的问题回答不够准确，希望知识库能再丰富一些。", "reviewed"),
            # 中性/负向反馈
            ("126****1357", "景区设施", 3, "景区指示牌不太清楚，找了半天洗手间，幸好问了灵小游才找到。建议增加实体指引。", "reviewed"),
            ("125****8024", "排队体验", 2, "国庆期间人太多了，抱佛脚排了一个小时队！灵小游建议的错峰时间在节假日不太管用。", "reviewed"),
            ("124****6913", "交通出行", 2, "停车场离入口太远，带着老人走了快20分钟才到大门口，景区内观光车班次也不够。", "reviewed"),
            ("123****5802", "餐饮服务", 3, "素斋种类有点少，价格偏贵。灵小游推荐的餐厅到了发现要排很久的队。", "reviewed"),
            ("122****4791", "票务服务", 2, "线上买票系统反应太慢了，支付了两次才成功，还好客服及时处理了退款。", "reviewed"),
            ("121****3680", "网络体验", 1, "景区WiFi太差了！在山顶灵小游完全连不上，语音对话功能基本用不了，体验大打折扣。", "reviewed"),
            ("120****2579", "体验建议", 3, "数字人形象很可爱但有时候口型对不上，建议优化。另外希望增加方言版本的语音。", "reviewed"),
            ("119****1468", "信息服务", 2, "查天气功能经常延迟，问景区实时人流也查不到，希望数字人能接入更多实时数据。", "reviewed"),
            ("118****0357", "无障碍", 1, "老人轮椅在部分路段通行不便，灵小游没有提前告知无障碍路线，希望能增加这方面的信息。", "reviewed"),
            ("117****9246", "演出体验", 4, "《吉祥颂》太棒了！就是梵宫里有点冷，夏天去记得带件外套。灵小游提醒带外套很贴心。", "reviewed"),
            ("116****8135", "景点评价", 5, "拈花湾晚上灯光秀绝美！灵小游准确告知了19:00亮灯时间，拍了好多好看的照片。", "reviewed"),
            ("115****7024", "整体体验", 4, "整体来说这次灵山之旅很愉快，AI导游是加分项。建议在节假日增加服务器资源避免卡顿。", "reviewed"),
            ("114****6913", "特色体验", 5, "禅茶体验太赞了，无尽意斋的茶香让人心静。灵小游的文化讲解让体验更有深度。", "reviewed"),
        ]
        today = datetime.now()
        for i, fb in enumerate(feedbacks):
            days_ago = random.randint(0, 60)
            fb_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO feedbacks (phone, type, rating, content, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (*fb, fb_date),
            )
        print(f"[数据库] 反馈样本数据 {len(feedbacks)} 条")

    # ---- 对话记录 ----
    cur.execute("SELECT COUNT(*) AS cnt FROM chat_records")
    if cur.fetchone()["cnt"] == 0:
        sessions = {
            "sess_demo_01": [
                ("user", "你好，你是谁？"),
                ("assistant", "我是灵山景区智能助手灵小游 🪷 可以为您提供景点介绍、路线规划、门票信息、演出时间等服务。请问您想了解什么？"),
                ("user", "灵山大佛有什么故事？"),
                ("assistant", "灵山大佛是世界最高露天青铜释迦牟尼立像，通高88米……唐玄奘途经马山见山形酷似印度灵鹫山而命名'小灵山'。右手施无畏印，左手施与愿印，216级登云道暗合108烦恼与108愿望。"),
                ("user", "太好了，今天开放吗？"),
                ("assistant", "灵山胜境每天正常开放，主要景区07:00-17:30。室内场馆如梵宫、五印坛城09:00-17:00。欢迎来参观！"),
            ],
            "sess_demo_02": [
                ("user", "帮我规划2小时游览路线"),
                ("assistant", "佛国入门精华游（2-3小时）：①灵山大照壁打卡 → ②九龙灌浴看演出接圣水 → ③灵山大佛抱佛脚俯瞰太湖。建议10点入园赶九龙灌浴首场！"),
                ("user", "九龙灌浴几点有演出？"),
                ("assistant", "平日演出时间：10:00 / 11:30 / 13:30 / 15:00，每场约15-20分钟。提前10分钟到场正面视角最佳，演出后可接取圣水祈福。"),
                ("user", "谢谢，太详细了！"),
                ("assistant", "不客气！祝您游览愉快，有任何问题随时问我 🪷"),
            ],
            "sess_demo_03": [
                ("user", "门票多少钱"),
                ("assistant", "灵山胜境门票：成人票210元，半价票105元（6-18周岁/学生/60-69岁老人），免票（6周岁以下/70岁以上/军人/残疾人）。联票225元（门票+观光车）更划算！"),
                ("user", "有什么优惠政策"),
                ("assistant", "半价票105元适用：6-18周岁、全日制学生、60-69周岁老人。免票适用：6周岁以下/1.2米以下儿童、70周岁以上、现役军人、残疾人。推荐联票225元。"),
            ],
            "sess_demo_04": [
                ("user", "梵宫有什么看点"),
                ("assistant", "灵山梵宫被誉为'东方卢浮宫'，72000平方米，获鲁班奖。三大核心：28米高纯金星空穹顶、《华藏世界》琉璃巨制、东阳木雕群。《吉祥颂》每日4场，凭门票免费观看。"),
                ("user", "吉祥颂演出在哪里看"),
                ("assistant", "《灵山吉祥颂》在灵山梵宫圣坛，每日10:35/11:30/14:00/16:00共4场，每场20分钟，全球唯一大型旋转舞台+全息投影。凭大门票免费！提前30分钟到场效果最佳。"),
                ("user", "午餐吃什么"),
                ("assistant", "推荐梵宫素斋自助约50元/位，素面套餐约35元/位。灵山精舍也有素斋，无尽意斋和拈花堂提供免费禅茶。"),
            ],
            "sess_demo_05": [
                ("user", "带小孩怎么玩"),
                ("assistant", "亲子家庭轻松游（4小时）：①九龙灌浴 → ②天下第一掌摸掌祈福 → ③百子戏弥勒亲子互动 → ④灵山梵宫看《吉祥颂》 → ⑤五印坛城转经筒。建议9点前入园，梵宫素斋50元/位。"),
                ("user", "百子戏弥勒在哪里"),
                ("assistant", "百子戏弥勒在灵山大佛脚下的广场区域，是座高3米宽7.8米的青铜群雕，弥勒佛笑容可掬，百名孩童形态各异。免费观赏，触摸弥勒肚皮寓意'享一生福气'！"),
            ],
            "sess_demo_06": [
                ("user", "今天天气怎么样"),
                ("assistant", "无锡灵山今天晴，温度28°C，体感30°C，湿度65%，微风。适宜出游，建议注意防晒，带好饮用水。"),
                ("user", "好的，帮我推荐个5小时的路线"),
                ("assistant", "自然风光全景游（5小时）：佛足坛 → 九龙灌浴 → 菩提大道 → 灵山大佛俯瞰太湖日落 → 曼飞龙塔。推荐下午入园，傍晚在灵山大佛平台拍摄太湖日落，佛光普照美不胜收！"),
            ],
            "sess_demo_07": [
                ("user", "这里人多不多"),
                ("assistant", "目前景区人流适中。根据经验，上午10点前和下午3点后是人流较少的时段。节假日和周末人会多一些，建议提前一天规划行程。"),
                ("user", "观光车在哪里坐"),
                ("assistant", "观光车在景区入口及各主要景点均设有站点，单独购票40元/人。推荐购买联票225元（门票+观光车无限次乘坐），省时省力。老人和带小孩的家庭特别推荐！"),
            ],
            "sess_demo_08": [
                ("user", "祥符禅寺有什么历史"),
                ("assistant", "祥符禅寺是千年古刹，始建于唐贞观年间，由玄奘弟子窥基大师开坛讲经。北宋赐额'祥符禅寺'。三大遗存：千年银杏、六角古井（茶圣陆羽品鉴）、江南第一钟（12.8吨），可撞钟祈福。"),
                ("user", "太震撼了"),
                ("assistant", "是的！千年古刹底蕴深厚，秋季银杏金黄时更是绝美。建议预留30分钟慢慢体验，别忘了撞钟祈福哦 🪷"),
            ],
        }
        today = datetime.now()
        for sess_id, messages in sessions.items():
            for j, (role, content) in enumerate(messages):
                minutes_ago = len(messages) - j + random.randint(0, 120)
                created = (today - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")
                src = None
                if role == "assistant":
                    if "景点" in content or "大佛" in content or "梵宫" in content or "禅寺" in content:
                        src = "knowledge"
                    elif "门票" in content or "价格" in content or "优惠" in content or "路线" in content or "亲子" in content:
                        src = "faq"
                    elif "天气" in content:
                        src = "weather"
                    else:
                        src = "ai"
                cur.execute(
                    "INSERT INTO chat_records (phone, session_id, role, content, source, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    ("138****0000", sess_id, role, content, src, created),
                )
        print(f"[数据库] 对话记录样本 {sum(len(m) for m in sessions.values())} 条")
