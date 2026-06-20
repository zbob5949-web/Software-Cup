# -*- coding: utf-8 -*-
"""
database.py
数据库连接、建表、初始化数据
其他模块优先通过 dependencies.get_db 依赖注入获取连接
"""
import pymysql
import os
import threading
from queue import Empty, LifoQueue

# ====================== 数据库配置 ======================
from core.config import DB_CONFIG as _BASE_CONFIG
from core.config import ADMIN_PHONE, ADMIN_PASSWORD, DB_POOL_SIZE, DB_POOL_TIMEOUT

DB_CONFIG = {
    "host": os.getenv("DB_HOST", _BASE_CONFIG["host"]),
    "port": int(os.getenv("DB_PORT", str(_BASE_CONFIG["port"]))),
    "user": os.getenv("DB_USER", _BASE_CONFIG["user"]),
    "password": os.getenv("DB_PASSWORD", _BASE_CONFIG["password"]),
    "database": os.getenv("DB_NAME", _BASE_CONFIG["database"]),
    "charset": "utf8mb4",
    "autocommit": False,
}

# 启动时检查密码是否已配置
if not DB_CONFIG["password"]:
    print("[数据库] 警告: 未设置 DB_PASSWORD 环境变量，请通过环境变量配置数据库密码")


def _create_raw_connection():
    conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)
    conn.cursorclass = pymysql.cursors.DictCursor
    return conn


class _PooledConnection:
    """轻量连接池代理：close() 归还连接，而不是直接断开。"""

    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._pool.release(self._conn)


class _ConnectionPool:
    def __init__(self, maxsize: int):
        self._maxsize = max(1, maxsize)
        self._idle = LifoQueue(maxsize=self._maxsize)
        self._created = 0
        self._lock = threading.Lock()

    def _new_connection(self):
        with self._lock:
            if self._created >= self._maxsize:
                return None
            self._created += 1
        try:
            return _create_raw_connection()
        except Exception:
            with self._lock:
                self._created = max(0, self._created - 1)
            raise

    def _discard(self, conn):
        try:
            conn.close()
        except Exception:
            pass
        with self._lock:
            self._created = max(0, self._created - 1)

    def acquire(self):
        conn = None
        try:
            try:
                conn = self._idle.get_nowait()
            except Empty:
                conn = self._new_connection()
                if conn is None:
                    conn = self._idle.get(timeout=DB_POOL_TIMEOUT)

            try:
                conn.ping(reconnect=True)
            except Exception:
                self._discard(conn)
                conn = self._new_connection()
            return _PooledConnection(conn, self)
        except Exception as e:
            print(f"[数据库] 连接失败: {e}")
            return None

    def release(self, conn):
        try:
            # 防止未提交事务污染下一次请求
            conn.rollback()
            conn.ping(reconnect=True)
            self._idle.put_nowait(conn)
        except Exception:
            self._discard(conn)

    def close_all(self):
        while True:
            try:
                conn = self._idle.get_nowait()
            except Empty:
                break
            self._discard(conn)


_POOL = _ConnectionPool(DB_POOL_SIZE)


def get_db_connection():
    return _POOL.acquire()


def close_db_pool():
    _POOL.close_all()

def init_database():
    conn = get_db_connection()
    if not conn:
        print("[数据库] 初始化失败")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(11) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    INDEX idx_phone (phone)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verification_sessions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(11) NOT NULL,
                    code VARCHAR(6) NOT NULL,
                    code_type VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    INDEX idx_phone (phone),
                    INDEX idx_expires (expires_at),
                    INDEX idx_type (code_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_records (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(15) NULL,
                    session_id VARCHAR(64) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    source VARCHAR(30) NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_phone_session (phone, session_id, created_at),
                    INDEX idx_role_source (role, source)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS spots (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(50),
                    description TEXT,
                    open_time VARCHAR(100),
                    duration VARCHAR(50),
                    tips TEXT,
                    sort_order INT DEFAULT 0,
                    image_url VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS routes (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    duration VARCHAR(50),
                    difficulty VARCHAR(20),
                    description TEXT,
                    spot_ids VARCHAR(255),
                    hours_min INT DEFAULT 0,
                    hours_max INT DEFAULT 24,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(11),
                    type VARCHAR(50) NOT NULL,
                    rating INT NOT NULL,
                    content TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_phone (phone),
                    INDEX idx_type (type),
                    INDEX idx_rating (rating)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(11) NOT NULL,
                    spot_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_phone_spot (phone, spot_id),
                    INDEX idx_phone (phone)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS faqs (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    question VARCHAR(255) NOT NULL,
                    answer TEXT NOT NULL,
                    category VARCHAR(50),
                    keywords VARCHAR(255) DEFAULT NULL,
                    sort_order INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS digital_human_configs (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    voice_name VARCHAR(100) DEFAULT 'zh-CN-XiaoxiaoNeural',
                    voice_style VARCHAR(100) DEFAULT NULL,
                    appearance TEXT,
                    clothing TEXT,
                    cultural_style TEXT,
                    keywords TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_reports (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    source VARCHAR(20) DEFAULT 'local',
                    summary TEXT,
                    positive_count INT DEFAULT 0,
                    neutral_count INT DEFAULT 0,
                    negative_count INT DEFAULT 0,
                    suggestions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_period (period_start, period_end)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        conn.commit()
        print("[数据库] 建表完成")
        _migrate_schema(conn)
        _seed_data(conn)
    except Exception as e:
        print(f"[数据库] 建表失败: {e}")
    finally:
        conn.close()

def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    return cursor.fetchone()["cnt"] > 0

def _index_exists(cursor, table_name: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table_name, index_name),
    )
    return cursor.fetchone()["cnt"] > 0

def _migrate_schema(conn):
    """Keep older local databases compatible with the current API code."""
    try:
        with conn.cursor() as cur:
            if not _column_exists(cur, "chat_records", "phone"):
                cur.execute("ALTER TABLE chat_records ADD COLUMN phone VARCHAR(15) NULL AFTER id")
            if not _column_exists(cur, "chat_records", "session_id"):
                cur.execute("ALTER TABLE chat_records ADD COLUMN session_id VARCHAR(64) NOT NULL DEFAULT '' AFTER phone")
            if not _column_exists(cur, "chat_records", "role"):
                cur.execute("ALTER TABLE chat_records ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user' AFTER session_id")
            if not _column_exists(cur, "chat_records", "created_at"):
                cur.execute(
                    "ALTER TABLE chat_records "
                    "ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                )
            if _column_exists(cur, "chat_records", "username"):
                cur.execute("ALTER TABLE chat_records MODIFY COLUMN username VARCHAR(64) NULL")
            if not _column_exists(cur, "chat_records", "source"):
                cur.execute("ALTER TABLE chat_records ADD COLUMN source VARCHAR(30) NULL AFTER content")
            if not _index_exists(cur, "chat_records", "idx_phone_session"):
                cur.execute(
                    "ALTER TABLE chat_records "
                    "ADD INDEX idx_phone_session (phone, session_id, created_at)"
                )
            if not _index_exists(cur, "chat_records", "idx_role_source"):
                cur.execute("ALTER TABLE chat_records ADD INDEX idx_role_source (role, source)")
            if not _column_exists(cur, "users", "role"):
                cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' AFTER password")
            if _column_exists(cur, "verification_sessions", "code"):
                cur.execute("ALTER TABLE verification_sessions MODIFY COLUMN code VARCHAR(6) NOT NULL")
            # FAQ 管理后台依赖以下列；旧库如果只有 question/answer/category，需要自动补齐。
            if not _column_exists(cur, "faqs", "keywords"):
                cur.execute("ALTER TABLE faqs ADD COLUMN keywords VARCHAR(255) DEFAULT NULL AFTER category")
            if not _column_exists(cur, "faqs", "sort_order"):
                cur.execute("ALTER TABLE faqs ADD COLUMN sort_order INT DEFAULT 0 AFTER keywords")
            if not _column_exists(cur, "faqs", "is_active"):
                cur.execute("ALTER TABLE faqs ADD COLUMN is_active BOOLEAN DEFAULT TRUE AFTER sort_order")
            if not _column_exists(cur, "faqs", "created_at"):
                cur.execute("ALTER TABLE faqs ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            # 游客反馈统计依赖 status；旧库自动补齐。
            if not _column_exists(cur, "feedbacks", "status"):
                cur.execute("ALTER TABLE feedbacks ADD COLUMN status VARCHAR(20) DEFAULT 'pending' AFTER content")
            # 数字人配置与感受度报告表：若旧版本没有，建表语句已覆盖；这里补齐可能缺失的列。
            digital_columns = [
                ("voice_name", "VARCHAR(100) DEFAULT 'zh-CN-XiaoxiaoNeural'"),
                ("voice_style", "VARCHAR(100) DEFAULT NULL"),
                ("appearance", "TEXT"),
                ("clothing", "TEXT"),
                ("cultural_style", "TEXT"),
                ("keywords", "TEXT"),
                ("is_active", "BOOLEAN DEFAULT FALSE"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ]
            for column_name, definition in digital_columns:
                if not _column_exists(cur, "digital_human_configs", column_name):
                    cur.execute(f"ALTER TABLE digital_human_configs ADD COLUMN {column_name} {definition}")
        conn.commit()
        print("[数据库] 表结构检查完成")
    except Exception as e:
        conn.rollback()
        print(f"[数据库] 表结构迁移失败: {e}")

def _seed_data(conn):
    """写入景区基础数据(只在表为空时执行)"""
    try:
        with conn.cursor() as cur:
            # ===== 景点数据（23条，严格按CSV资料） =====
            cur.execute("SELECT COUNT(*) AS cnt FROM spots")
            if cur.fetchone()['cnt'] == 0:
                spots = [
                    # ---- 灵山胜境 ----
                    ("灵山大照壁", "建筑",
                     "景区入口标志性建筑，被誉为'华夏第一壁'。长39.8米，高7米，最厚处1.9米，采用优质青石雕刻而成。"
                     "正面是赵朴初先生亲笔题写的鎏金'灵山胜境'四字，背面刻有赵老诗作《小灵山》，"
                     "将无锡小灵山与印度灵鹫山相媲美，奠定了整个景区的佛教文化基调。"
                     "照壁两侧与碧波荡漾的太湖交相辉映，构成'湖光山色共一楼'的壮美景观。",
                     "全天开放", "15分钟",
                     "进园第一处打卡点，正面拍摄鎏金大字最佳，可与太湖背景同框留念；"
                     "如愿火车站装置为小众取景框，搭配照壁与太湖背景，可拍出独具特色的禅意照片。",
                     1, None),
                    ("五明桥", "建筑",
                     "横跨香水海的五座汉白玉石拱桥，代表佛教中的五种核心智慧：声明（语言学）、因明（逻辑学）、"
                     "内明（哲学）、医方明（医学）、工巧明（工艺学），寓意过桥即能开启智慧、走向觉悟。"
                     "桥栏雕刻莲花、飞天、神兽等精美佛教图案，石桥倒映在香水海碧波中，意境悠远。",
                     "全天开放", "10分钟",
                     "漫步过桥时可一一对应五种智慧，拍摄桥与水面倒影构图绝佳；"
                     "是连接入口区域与核心朝圣区域的必经之路。",
                     2, None),
                    ("佛足坛", "建筑",
                     "复刻佛祖释迦牟尼真身脚印，巨型青铜佛足印一对，左右对称，每只足印长1.2米、宽0.6米，"
                     "采用整块青铜铸造，表面经过特殊防腐处理，色泽温润。"
                     "足心刻有千辐轮相、宝瓶鱼纹等32种吉祥图案，象征'佛足所至，佛光普照'，"
                     "代表佛的福德与智慧圆满。相传佛祖涅槃前留下双足印，称为'两足尊''。",
                     "全天开放", "10分钟",
                     "可亲手触摸足心32种吉祥图案，寄托祈福心愿；"
                     "是进入核心景区前的重要朝圣节点，与灵山大佛遥相呼应。",
                     3, None),
                    ("五智门", "建筑",
                     "核心景区门户，高16.8米、宽35米，五门六柱汉白玉石牌坊造型。"
                     "五门分别象征五方五佛，代表佛教的全域覆盖与普度众生；"
                     "六柱代表佛教'六度波罗蜜'——布施、持戒、忍辱、精进、禅定、般若，"
                     "门柱上刻有对应经文，字字珠玑。穿过这道门，便从'凡俗之境'踏入'禅意圣地'。"
                     "整座牌坊与后方灵山大佛在同一中轴线上。",
                     "全天开放", "10分钟",
                     "穿门祈福，门柱上的六度经文值得驻足细读；夜间有灯光点缀，氛围感更佳；"
                     "是景区中轴线景观的重要组成部分。",
                     4, None),
                    ("菩提大道", "建筑",
                     "五智门北侧直通九龙灌浴广场，长约250米、宽约10米的朝圣步道。"
                     "两侧对称种植近百棵从印度引进的正宗菩提树，枝繁叶茂，形成天然禅意拱廊，"
                     "象征佛陀在菩提树下悟道成佛，营造清净悠远的禅境。"
                     "微风拂过，菩提叶沙沙作响，宛如佛音萦绕耳畔。",
                     "全天开放", "10分钟",
                     "春季菩提花开时景致绝美，可观赏白色菩提花；"
                     "夏季林荫拱廊是绝佳避暑步道；还可捡拾菩提叶制作书签留念。",
                     5, None),
                    ("九龙灌浴", "演出",
                     "灵山胜境最具标志性的动态景观，总高27.2米，耗铜量达260吨。"
                     "核心为7.2米高的鎏金太子佛，重12吨，周围环绕9组72只凤凰雕塑和九条飞龙。"
                     "依据《本行经》中释迦牟尼诞生传说打造，生动再现'花开见佛，九龙沐浴'的祥瑞景象。"
                     "专属背景音乐《佛之诞》响起时，莲花铜雕缓缓绽放，太子佛升起并自转一周，"
                     "九条飞龙同时喷出水柱，高达数十米，水幕与阳光交织出七彩佛光，震撼人心。",
                     "平日演出：10:00 / 11:30 / 13:30 / 15:00（节假日增加场次，以景区广播为准）", "20分钟",
                     "景区必看！提前10分钟到场占位，正面视角效果最佳；"
                     "演出结束后可在广场两侧接取龙头流出的'圣水'，寓意祈福安康、沾取佛诞祥瑞之气。",
                     6, None),
                    ("降魔浮雕", "建筑",
                     "长26米、高4.6米的巨型花岗岩石雕，采用高浮雕与浅浮雕相结合的精湛手法。"
                     "中央佛陀端坐菩提树下，神情坚定、目光如炬；"
                     "两侧魔王波旬率魔女、魔兵以美色、财富、武力诱惑威胁，"
                     "佛陀沉稳无畏，最终战胜诱惑、觉悟成佛，传递'坚守本心、终能成道'的禅理。"
                     "人物表情、动作、服饰、发丝、衣纹均清晰可辨，是佛教雕刻艺术珍品。",
                     "全天开放", "15分钟",
                     "佛教文化核心科普点，了解佛陀'八相成道'的重要景观；"
                     "细看浮雕中魔女与佛陀表情的对比，感受艺术与文化的融合。",
                     7, None),
                    ("阿育王柱", "建筑",
                     "通高16.9米，直径1.8米，总重量180吨，采用整块优质花岗岩一次性雕刻而成。"
                     "复刻古印度阿育王石柱造型，柱身刻有经文，柱头四头狮子分别朝向东南西北四方，"
                     "象征佛法向世界各地传播，彰显佛教'和平、包容、普度'的核心精神。"
                     "阿育王是古印度最著名的弘法国王，统一印度后笃信佛教，将佛法传播至世界各地，"
                     "这根石柱是佛教从印度传入中国的重要历史象征。",
                     "全天开放", "10分钟",
                     "四狮柱头细节精美，与灵山大佛、五智门在同一中轴线上；"
                     "是景区中轴线核心景观序列的重要节点。",
                     8, None),
                    ("百子戏弥勒", "建筑",
                     "高3米、宽7.8米、重9吨的青铜群雕。弥勒佛呈卧姿，袒胸露腹、嘴角上扬，"
                     "笑容憨厚可掬，身上塑有百名嬉戏的孩童，形态各异、生动活泼。"
                     "弥勒佛是佛教中的未来佛，象征'欢喜、包容、慈悲'，"
                     "百子环绕寓意'多子多福、家庭和睦、子孙满堂'，"
                     "完美融合佛教'慈悲喜舍'与民间祈福愿望。群雕采用优质青铜铸造，工艺精美。",
                     "全天开放", "15分钟",
                     "触摸弥勒佛肚皮，寓意'摸弥勒肚皮，享一生福气'；"
                     "寻找百名孩童的不同姿态感受民间艺术；亲子互动拍照定格温馨瞬间。",
                     9, None),
                    ("祥符禅寺", "建筑",
                     "灵山胜境历史最悠久的人文景观，千年古刹。"
                     "始建于唐贞观年间，由玄奘弟子窥基大师开坛讲经；"
                     "北宋大中祥符年间（1008-1016年）宋真宗赐额'祥符禅寺'，历经千年香火绵延。"
                     "整体采用仿唐重檐歇山式建筑风格，包含弥勒殿、大雄宝殿、钟楼、鼓楼。"
                     "寺内珍贵遗存：千年古银杏（秋季金黄绝美）、六角古井（唐代名泉，茶圣陆羽品鉴过）、"
                     "钟楼内悬挂重12.8吨的'祥符禅钟'，被誉为'江南第一钟'，钟声浑厚洪亮，响彻山谷。",
                     "全天开放，宗教活动正常开展", "30分钟",
                     "可参与撞钟祈福，寓意'烦恼尽除、福慧增长'；"
                     "秋季可欣赏千年银杏金黄景致；是了解灵山千年历史的核心场所。",
                     10, None),
                    ("灵山大佛", "佛像",
                     "世界最高露天青铜释迦牟尼立像。佛像通高88米（佛体79米+莲花瓣9米），"
                     "含台基总高101.5米，耗铜量达725吨，由1560块6-8毫米厚铜壁板拼接而成，"
                     "焊缝总长度逾35公里。1994年奠基，1997年11月15日落成开光。"
                     "右手施无畏印（除却众生痛苦），左手施与愿印（赐予众生欢乐）。"
                     "216级登云道分两段：前108级为'烦恼尽除'，后108级为'愿望圆满'，"
                     "暗合佛教108烦恼与108愿望。体现赵朴初'五方五佛'理念，象征东方佛。",
                     "07:00-17:30（最后入园17:00）", "40分钟",
                     "必体验抱佛脚祈福；登顶可俯瞰太湖全景；"
                     "夕阳下金色阳光洒在大佛身上，'佛光普照'最为壮观，是拍照最佳时段。",
                     11, None),
                    ("天下第一掌", "体验",
                     "灵山大佛右手手掌的等比例复制品，高11.7米、宽5.5米，立于佛手广场。"
                     "游客可近距离触摸，称为'摸掌祈福'，寓意'沾福气、保平安'。"
                     "与'抱佛脚'并称灵山两大祈福体验，是景区内最受游客喜爱的互动景点之一。",
                     "07:00-17:30", "15分钟",
                     "站在掌心仰拍灵山大佛，角度绝佳；摸掌祈福是热门体验，祈求平安顺遂。",
                     12, None),
                    ("佛教文化博览馆", "建筑",
                     "设于灵山大佛三层座基内，总建筑面积10000平方米，免费向游客开放。"
                     "三层结构：一层展示五方五佛与中国佛教四大名山文化，配有实景沙盘；"
                     "二层以时间为轴介绍世界佛教发展史，设有'佛法东传'互动触屏区；"
                     "三层万佛殿以鎏金装饰和暖光照明，9999尊按1:100复刻的灵山大佛小像"
                     "整齐排布四周与穹顶，与室外大佛形成'万佛朝宗'的震撼格局。"
                     "馆内配备智能导览屏、沉浸式投影、文物复刻展柜等现代化设施。",
                     "08:00-17:00（冬季提前至16:30闭馆）", "40分钟",
                     "免费讲解时段：9:30/11:00/14:30/16:00，在一层入口集合即可；"
                     "万佛殿禁止闪光灯；沉浸式投影体验每30分钟循环一场。",
                     13, None),
                    ("灵山梵宫", "建筑",
                     "被誉为'东方卢浮宫'，建筑面积72000平方米，最高处66.5米，荣获鲁班奖。"
                     "第二、四届世界佛教论坛永久会址，圣坛可容纳2000人同时观演。"
                     "三大艺术核心：①28米高星空穹顶，用100公斤纯金绘制148尊飞天，"
                     "依据唐代《佛说炽盛光大威德消灾吉祥陀罗尼经》创作；"
                     "②《华藏世界》琉璃巨制，160块彩色琉璃拼接，宽8米高10米，2000吨琉璃熔铸，"
                     "翡翠镶嵌的菩提叶脉络在特定角度显现般若经文；"
                     "③东阳木雕群，以金丝楠木为主材，展现花卉、云纹、四灵等元素。"
                     "另有12幅高12米的'世界佛教传法图'油画、景泰蓝须弥灯、寿山石雕等非遗精品。",
                     "09:00-17:00（冬季提前至16:30闭馆）", "60-90分钟",
                     "凭景区大门票免费入场；《吉祥颂》演出每日10:35/11:30/14:00/16:00，"
                     "建议提前30分钟到场排队占座；禁止使用闪光灯。",
                     14, None),
                    ("五印坛城", "建筑",
                     "位于香水海中央独立圆岛，四面环水，环境清幽。五层重檐楼宇，总高约30米，"
                     "占地5000平方米，藏式碉楼风格，白墙红边金顶，被称为'小布达拉宫'。"
                     "以西藏拉萨布达拉宫雪村大门为原型设计山门，四门安置马宝、孔雀、共命鸟、象宝四尊青铜瑞兽。"
                     "'五印'代表五方五佛的五种手印，坛城是藏传佛教'曼陀罗道场'，象征宇宙圆满。"
                     "转经筒长廊环绕主殿，摆放108个纯铜转经筒，筒内装有藏文经文。"
                     "馆内唐卡采用天然矿物颜料绘制，百年色彩鲜艳。",
                     "09:00-17:00（冬季提前至16:30闭馆）", "40分钟",
                     "顺时针转动转经筒，寓意'转经一圈，福慧双增'；"
                     "登至五层顶层俯瞰香水海、灵山梵宫与灵山大佛全景；"
                     "可预约藏香制作体验（10:00/14:00，费用自理）。",
                     15, None),
                    ("曼飞龙塔", "建筑",
                     "代表南传佛教文化的核心建筑，完全复刻云南西双版纳景洪市曼飞龙白塔（又称'白塔'）。"
                     "主塔高16.9米，底部直径10米，由一座主塔与八座约8米小塔组成九塔组合，"
                     "九塔象征南传佛教的九种智慧和佛陀的九种功德。"
                     "塔身以白色花岗岩为主，表面浅浮雕刻有释迦牟尼成道图、阿罗汉像等南传佛教图案；"
                     "塔刹采用鎏金铜质，在阳光下熠熠生辉。"
                     "与灵山梵宫（汉传）、五印坛城（藏传）并列，展现佛教三大语系文化在灵山的齐聚。",
                     "全天开放", "20分钟",
                     "九塔组合搭配香水海与五印坛城背景拍照绝美；"
                     "对比三大语系建筑差异，感受佛教文化的多元性；夜间灯光亮化别有韵味。",
                     16, None),
                    ("无尽意斋", "建筑",
                     "完全以赵朴初先生北京故居为原型复刻的北京四合院建筑，2008年建成。"
                     "占地600平方米，青砖灰瓦、木质梁柱，门窗为传统雕花样式，院内种植海棠、石榴、翠竹。"
                     "'无尽意'取自佛教经典《无尽意菩萨经》，象征赵朴初先生对佛教文化传承的无尽初心。"
                     "正房分三个展区：生平事迹厅、灵山渊源厅（书信手稿合影）、书法作品厅（真迹与复刻）。"
                     "东西厢房设临时展厅与禅意茶室，提供免费禅茶品鉴。",
                     "09:00-17:00（冬季提前至16:30闭馆）", "30分钟",
                     "免费参观；在禅意茶室品鉴免费禅茶，感受禅茶一味；"
                     "书法作品真迹禁止闪光灯；是了解灵山人文底蕴的重要场所。",
                     17, None),
                    # ---- 拈花湾禅意小镇 ----
                    ("拈花广场", "建筑",
                     "拈花湾禅意小镇入口核心区域，小镇的门户与集散中心。"
                     "占地约8000平方米，中央矗立高12米'拈花微笑'主题青铜鎏金雕塑，"
                     "源自佛教'迦叶拈花、佛陀微笑'的典故，象征顿悟成佛。"
                     "广场采用青石板铺设，四周环绕景观绿植与中式景观灯，搭配小型水景喷泉，充满禅意。"
                     "是小镇大型开园仪式、禅意表演的举办场地，每日9:30举办开园仪式。",
                     "09:00-21:30（冬季提前至20:30闭园）", "15分钟",
                     "与'拈花微笑'雕塑打卡合影；夜间景观灯18:00点亮，氛围感极佳；"
                     "是进入拈花湾的第一站，可在此规划游览路线。",
                     18, None),
                    ("梵天花海", "自然",
                     "拈花湾小镇内规模最大的自然景观区，总占地约30000平方米。"
                     "种植格桑花、波斯菊、硫华菊、百日草等多种观赏性花卉，"
                     "实现'四季有花、四季有景'：春季格桑花粉色铺满大地，夏季硫华菊色彩艳丽，"
                     "秋季波斯菊再次绽放，冬季绿植依旧翠绿。"
                     "花海内木质步道总长约1500米，中央设中式歇山顶景观凉亭，以'花伴禅心'为核心内涵。",
                     "09:00-21:30（冬季提前至20:30闭园）", "30分钟",
                     "四季拍摄不同花卉，禁止采摘踩踏；夏季蚊虫较多建议做好防蚊措施；"
                     "建议白天游览，夜间无专门亮化。",
                     19, None),
                    ("香月花街", "建筑",
                     "拈花湾小镇核心商业街，贯穿小镇南北中轴线，全长约800米，宽8米。"
                     "建筑融合中式禅意与日式町屋特色，白墙黛瓦、飞檐翘角、雕花门窗，"
                     "街道两侧分布禅意文创、非遗手作、特色餐饮、禅茶品鉴等特色商铺。"
                     "可体验剪纸、陶艺、木刻等非遗手作；品尝素面、禅茶、江南小吃等特色美食；"
                     "选购佛珠、书签、香薰等禅意文创产品。夜间灯笼街巷氛围感十足。",
                     "09:00-21:30（冬季提前至20:30闭园），商铺9:30-21:00", "60分钟",
                     "夜间18:00点亮街道灯笼，建议白天逛文创夜间打卡灯光；"
                     "每日有不定时禅意巡游表演，具体以景区广播通知为准。",
                     20, None),
                    ("拈花堂", "建筑",
                     "拈花湾小镇最具禅意的静心场所，隐藏于香月花街东侧绿植之中，占地约1200平方米。"
                     "中式禅堂建筑，白墙黛瓦、朱红门窗，内设禅坐区、抄经区、禅茶区，"
                     "源自佛教'拈花悟禅'典故，传递'静心、修身、悟道'的禅理。"
                     "每日举办小型禅意讲座（10:30/15:30，无需预约，每场约40分钟）；"
                     "抄经区提供经文手稿、毛笔、墨汁，抄写经文后可自愿带走；"
                     "禅茶区有专业人员讲解禅茶礼仪，提供免费禅茶品鉴。",
                     "09:30-19:00（冬季提前至18:00闭馆）", "40分钟",
                     "进入需保持安静，手机调至静音；禁止携带零食饮料；"
                     "禅坐、抄经、禅茶品鉴均免费；建议穿着舒适素雅的衣物。",
                     21, None),
                    ("五灯湖", "自然",
                     "拈花湾小镇内最大的水景景观区，湖面面积约5000平方米，也是夜间灯光秀核心举办场地。"
                     "湖水清澈见底，湖底铺设鹅卵石，岸边种植垂柳、翠竹、荷花。"
                     "湖面设有木质栈道、景观桥、湖心亭（中式六角亭），"
                     "'五灯'象征'五智'，湖水象征'清净本心'。"
                     "夜间《禅行》灯光秀每日19:00/20:00各一场（每场约30分钟），"
                     "灯光投影装置投射禅意图案与经文，搭配水雾装置，如梦如幻。",
                     "09:00-21:30（冬季提前至20:30闭园）", "30分钟",
                     "夏季可赏荷花；夜间观看《禅行》灯光秀，拍摄灯光倒映湖面的绝美瞬间；"
                     "栈道夜间需注意安全，避免拥挤。",
                     22, None),
                    ("鹿鸣谷", "自然",
                     "拈花湾小镇西侧，处于山林之间，是小镇内最静谧的自然景观区。"
                     "占地约20000平方米，种植香樟、松柏、翠竹等多种绿植，植被覆盖率达90%以上，"
                     "谷内设有木质步道总长约1.5公里，空气清新，远离主客流，适合静心漫步。"
                     "是感受自然与禅意融合的绝佳场所，也是放松身心的理想去处。",
                     "随拈花湾小镇开放时间", "30-40分钟",
                     "步道为防腐木质结构，雨天注意防滑；适合喜爱清幽自然环境的游客；"
                     "建议傍晚时分游览，享受山林清幽与晚风。",
                     23, None),
                ]
                cur.executemany(""" 
                    INSERT IGNORE INTO spots 
                    (name, category, description, open_time, duration, tips, sort_order, image_url) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                """, spots)
                print("[数据库] 景点数据写入完成, 共 %d 条" % len(spots))

            # ===== 路线数据（4条，4h/5h/6h已更新为CSV内容） =====
            cur.execute("SELECT COUNT(*) AS cnt FROM routes")
            if cur.fetchone()['cnt'] == 0:
                routes = [
                    # 2-3h 入门（不变）
                    ("佛国入门精华游", "2-3小时", "入门",
                     "适合时间有限的初次访客，串联三大必打卡景点。"
                     "推荐路线：灵山大照壁→九龙灌浴→灵山大佛。"
                     "建议上午10点入园，赶上九龙灌浴10:00首场演出，再步行至大佛抱佛脚祈福。",
                     "1,6,11", 2, 3),
                    # 4h 亲子（更新为CSV路线）
                    ("亲子家庭轻松游", "4小时", "轻松",
                     "适合带孩子的家庭，涵盖最具趣味性与互动性的核心景点。"
                     "推荐路线：南门入园→九龙灌浴（观赏动态演出，讲述释迦牟尼诞生故事）"
                     "→佛手广场·天下第一掌（摸掌祈福互动）"
                     "→百子戏弥勒（亲子互动，感受皆大欢喜）"
                     "→灵山梵宫（欣赏穹顶天象图与琉璃艺术，《吉祥颂》演出）"
                     "→五印坛城（体验藏式转经筒祈福文化）→出口。"
                     "建议上午9点前入园，中途可在梵宫素斋自助（50元/位）用餐。",
                     "6,12,9,14,15", 3, 4),
                    # 5h 自然（更新为CSV路线）
                    ("自然风光全景游", "5小时", "普通",
                     "适合摄影爱好者与自然风光爱好者，串联景区最具景观性的节点。"
                     "推荐路线：南门入园→佛足坛（朝圣祈福）"
                     "→九龙灌浴（观赏表演，接取圣水，欣赏七彩佛光）"
                     "→菩提大道（漫步林荫，欣赏太湖风光与青龙白虎山的风水格局）"
                     "→灵山大佛（登顶俯瞰太湖全景，拍摄夕阳佛光）"
                     "→曼飞龙塔（欣赏南传佛教建筑美学）"
                     "→梵宫广场→出口。"
                     "推荐下午入园，在大佛平台拍摄太湖日落，'佛光普照'最为壮观。",
                     "3,6,5,11,16", 5, 5),
                    # 6h 历史文化（更新为CSV路线）
                    ("历史文化深度游", "6小时", "深度",
                     "适合历史文化爱好者，系统了解灵山1300多年佛教渊源与传统艺术精髓。"
                     "推荐路线：南门入园→灵山大照壁（华夏第一壁，解读赵朴初书法与《小灵山》诗刻）"
                     "→天下第一掌·佛手广场（摸掌祈福）"
                     "→祥符禅寺（千年古刹历史讲解，参与撞钟祈福，观赏千年银杏与六角古井）"
                     "→灵山大佛（佛教造像艺术解析，五方五佛理念，216级登云道文化寓意）"
                     "→灵山梵宫（佛教艺术殿堂深度游，《吉祥颂》演出，穹顶/琉璃/木雕三大艺术核心）"
                     "→五印坛城（藏传佛教文化体验，转经筒，唐卡欣赏）"
                     "→出口。建议预约景区导游讲解服务（300元起）。",
                     "1,12,10,11,14,15", 6, 8),
                ]
                cur.executemany(""" 
                    INSERT IGNORE INTO routes 
                    (name, duration, difficulty, description, spot_ids, hours_min, hours_max) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s) 
                """, routes)
                print("[数据库] 路线数据写入完成, 共 %d 条" % len(routes))

            # ===== FAQ 数据（26条，按CSV门票信息与文化背景大幅扩充） =====
            cur.execute("SELECT COUNT(*) AS cnt FROM faqs")
            if cur.fetchone()['cnt'] == 0:
                faqs = [
                    # ---- 开放时间 ----
                    ("今天开放吗？",
                     "灵山胜境景区每天正常开放，主要景区开放时间为 **07:00-17:30**（最后入园17:00）。\n\n"
                     "**室内场馆单独时间：**\n"
                     "- 灵山梵宫、五印坛城、无尽意斋：**09:00-17:00**（冬季16:30闭馆）\n"
                     "- 佛教文化博览馆：**08:00-17:00**（冬季16:30闭馆）\n"
                     "- 拈花湾禅意小镇：**09:00-21:30**（冬季20:30闭园）\n\n"
                     "如遇特殊情况请以景区当日公告为准。",
                     "开放时间", "今天,开放,营业,开门,几点开,开放时间", 1),
                    ("梵宫几点开放？",
                     "**灵山梵宫** 开放时间为 **09:00-17:00**，冬季闭馆时间提前至 **16:30**。\n\n"
                     "梵宫内《吉祥颂》演出每日 **10:35 / 11:30 / 14:00 / 16:00** 共4场，每场约20分钟，"
                     "凭景区大门票免费入场。建议提前30分钟到场排队占座。\n\n"
                     "梵宫内禁止使用闪光灯，拍照需注意。",
                     "开放时间", "梵宫,开放时间,几点,梵宫开放", 2),
                    # ---- 门票 ----
                    ("门票多少钱？",
                     "灵山胜境门票价格：\n\n"
                     "- **成人票：210元**（18周岁以上成年人）\n"
                     "- **半价票：105元**（6-18周岁未成年、全日制本科及以下学生、60-69周岁老人）\n"
                     "- **免票（0元）**：6周岁以下/70周岁以上老人/现役军人/残疾人\n"
                     "- **网购联票：225元**（门票+观光车无限次乘坐，更划算！）\n"
                     "- **观光车单独购票：40元/人**（景区内交通，适合体力有限的游客）\n\n"
                     "**梵宫《吉祥颂》演出凭景区大门票免费观看。**\n"
                     "以上价格仅供参考，请以景区官方渠道公示价格为准。",
                     "票价", "门票,价格,多少钱,票价,费用,票", 3),
                    ("有什么优惠政策吗？",
                     "灵山胜境景区优惠政策：\n\n"
                     "**半价票（105元）：** 6-18周岁未成年人、全日制本科及以下学生（凭学生证）、60-69周岁老人\n\n"
                     "**免票（0元）：** 6周岁以下或1.2米以下儿童、70周岁以上老人、现役军人、残疾人\n\n"
                     "**最划算选择：网购联票225元** = 门票210元 + 观光车无限次乘坐（单独买观光车40元/人）\n\n"
                     "建议提前在官方小程序或官网购票，方便快捷。",
                     "票价", "优惠,半价,免票,学生,优惠政策,折扣", 4),
                    ("观光车在哪里坐？多少钱？",
                     "景区内设有观光车服务，方便体力有限的游客游览。\n\n"
                     "**价格：** 单独购票 **40元/人**，或购买 **网购联票225元**（含门票+观光车无限次）更划算。\n\n"
                     "**乘坐点：** 景区内多处设有观光车站点，入园后可按指示牌找到乘坐点，"
                     "具体路线以景区内实际标识为准。\n\n"
                     "建议老人、儿童、行动不便的游客购买联票，节省体力。",
                     "票价", "观光车,在哪,多少钱,交通,坐车", 5),
                    # ---- 演出 ----
                    ("九龙灌浴几点有演出？",
                     "《九龙灌浴》演出时间（平日）：\n"
                     "- **上午：10:00 / 11:30**\n"
                     "- **下午：13:30 / 15:00**\n\n"
                     "每场时长约 **15-20分钟**，周末及节假日会增加演出场次（以景区广播通知为准）。"
                     "建议提前 **10分钟** 到场，**正面视角** 观赏效果最佳。\n\n"
                     "**温馨提示：** 演出结束后可在广场两侧接取龙头流出的'圣水'，寓意祈福安康。"
                     "晴天时水幕与阳光交织出七彩佛光，美不胜收。",
                     "演出", "九龙灌浴,演出,几点,时间,表演", 6),
                    ("吉祥颂演出在哪里看？",
                     "**《灵山吉祥颂》** 大型演出在 **灵山梵宫圣坛** 上演。\n\n"
                     "**演出时间：** 每日 **10:35 / 11:30 / 14:00 / 16:00** 共4场，每场约20分钟。\n\n"
                     "**购票：** 凭景区大门票 **免费入场**，无需额外购票。\n\n"
                     "**亮点：** 圣坛设全球唯一大型旋转舞台，运用全息投影、水雾、激光等现代科技，"
                     "沉浸式演绎佛陀成道故事，震撼人心。\n\n"
                     "建议提前30分钟到场，确保有好的观演位置。",
                     "演出", "吉祥颂,梵宫,演出,在哪,表演", 7),
                    # ---- 路线推荐 ----
                    ("帮我规划2小时游览路线",
                     "为您推荐 **佛国入门精华游（2-3小时）** 路线：\n\n"
                     "① **灵山大照壁**（打卡入园第一景，感受华夏第一壁的恢弘）\n"
                     "② **九龙灌浴**（必看！花开见佛动态演出，接取圣水祈福）\n"
                     "③ **灵山大佛**（抱佛脚祈福，俯瞰太湖全景）\n\n"
                     "**建议：** 上午10点入园，赶上九龙灌浴10:00首场演出，"
                     "再步行至大佛，时间轻松充裕。",
                     "路线推荐", "2小时,入门,精华,路线,规划", 8),
                    ("帮我规划4小时游览路线",
                     "为您推荐 **亲子家庭轻松游（4小时）** 路线：\n\n"
                     "① **九龙灌浴**（动态演出，讲述释迦牟尼诞生故事）\n"
                     "② **天下第一掌**（摸掌祈福，'沾福气、保平安'）\n"
                     "③ **百子戏弥勒**（亲子互动，摸弥勒肚皮祈福）\n"
                     "④ **灵山梵宫**（欣赏穹顶艺术，观看《吉祥颂》演出）\n"
                     "⑤ **五印坛城**（体验藏式转经筒，感受'福慧双增'）\n\n"
                     "**建议：** 上午9点前入园，中途在梵宫素斋自助（50元/位）用餐。",
                     "路线推荐", "4小时,亲子,规划路线,游览,家庭", 9),
                    ("帮我规划5小时游览路线",
                     "为您推荐 **自然风光全景游（5小时）** 路线：\n\n"
                     "① **佛足坛**（朝圣祈福，触摸32种吉祥图案）\n"
                     "② **九龙灌浴**（观赏演出，接取圣水，欣赏七彩佛光）\n"
                     "③ **菩提大道**（漫步林荫步道，感受'前有照、后有靠'的风水格局）\n"
                     "④ **灵山大佛**（登顶俯瞰太湖全景，拍摄夕阳佛光）\n"
                     "⑤ **曼飞龙塔**（欣赏南传佛教建筑，感受三大语系佛教文化）\n\n"
                     "**最佳时间：** 下午入园，在大佛平台拍摄太湖日落，'佛光普照'最壮观。",
                     "路线推荐", "5小时,自然,摄影,规划路线,风光", 10),
                    ("帮我规划6小时深度游",
                     "为您推荐 **历史文化深度游（6小时）** 路线：\n\n"
                     "① **灵山大照壁**（华夏第一壁，解读赵朴初书法与《小灵山》诗刻）\n"
                     "② **天下第一掌**（摸掌祈福）\n"
                     "③ **祥符禅寺**（千年古刹，参与撞钟，观赏千年银杏与六角古井）\n"
                     "④ **灵山大佛**（佛教造像艺术解析，五方五佛，216级登云道文化寓意）\n"
                     "⑤ **灵山梵宫**（穹顶/琉璃/木雕三大艺术核心，《吉祥颂》演出）\n"
                     "⑥ **五印坛城**（藏传佛教，转经筒，唐卡欣赏）\n\n"
                     "**建议：** 预约景区导游讲解服务（300元起），深度了解每处景点背后的历史。",
                     "路线推荐", "6小时,深度,历史,文化,深度游", 11),
                    # ---- 景点介绍 ----
                    ("灵山大佛有什么故事？",
                     "**灵山大佛** 是 **世界最高露天青铜释迦牟尼立像**，通高 **88米**，含台基总高 **101.5米**，"
                     "耗铜量达 **725吨**，由1560块铜壁板拼接，焊缝总长逾35公里。\n\n"
                     "**为何建在灵山？** 1300多年前唐贞观年间，玄奘法师途经马山，"
                     "见此地'山形酷似印度灵鹫山'，遂命名为'小灵山'，此地自此与佛教结缘。\n\n"
                     "**五方五佛理念：** 中国佛教协会会长赵朴初认为东方空缺，"
                     "遂提出在无锡建造灵山大佛，与香港天坛大佛、四川乐山大佛、山西云冈大佛、"
                     "河南龙门大佛共同构成中国'五方五佛'格局。\n\n"
                     "**落成时间：** 1994年奠基，**1997年11月15日** 落成开光。\n\n"
                     "**手印含义：** 右手 **施无畏印**（除却众生痛苦），左手 **施与愿印**（赐予众生欢乐）。\n\n"
                     "**216级登云道：** 分两段，前108级为'烦恼尽除'，后108级为'愿望圆满'。",
                     "景点介绍", "灵山大佛,故事,介绍,历史,大佛", 12),
                    ("梵宫有什么看点？",
                     "**灵山梵宫** 被誉为 **'东方卢浮宫'**，荣获鲁班奖，建筑面积72000平方米，"
                     "世界佛教论坛永久会址。\n\n"
                     "**三大艺术核心：**\n"
                     "1. **星空穹顶** - 28米高，用 **100公斤纯金** 绘制148尊飞天，"
                     "依据唐代《佛说炽盛光大威德消灾吉祥陀罗尼经》创作\n"
                     "2. **《华藏世界》琉璃巨制** - 160块彩色琉璃，宽8米高10米，2000吨琉璃熔铸，"
                     "翡翠镶嵌的菩提叶脉络在特定角度显现般若经文\n"
                     "3. **东阳木雕群** - 金丝楠木为主材，展现花卉、云纹、四灵等元素\n\n"
                     "**另有：** 12幅高12米的'世界佛教传法图'油画、景泰蓝须弥灯、寿山石雕等非遗精品。\n\n"
                     "**必看演出：《灵山吉祥颂》** - 每日10:35/11:30/14:00/16:00，凭门票免费观看。",
                     "景点介绍", "梵宫,看点,介绍,东方卢浮宫,梵宫艺术", 13),
                    ("祥符禅寺有什么历史？",
                     "**祥符禅寺** 是灵山胜境历史最悠久的人文景观，千年古刹。\n\n"
                     "**起源（唐代）：** 唐贞观年间，玄奘法师命大弟子窥基法师在此住持道场，"
                     "兴建小灵山庵，奠定佛教根基。\n\n"
                     "**赐名（北宋）：** 大中祥符年间（1008-1016年），宋真宗赐额 **'祥符禅寺'**，"
                     "成为江南名刹。此后历经南宋兵燹、元代重建、明代鼎盛、清末战火。\n\n"
                     "**三大历史遗存：**\n"
                     "1. **千年银杏** - 秋季金黄绝美，见证寺院千年兴衰\n"
                     "2. **六角古井** - 唐代名泉，**茶圣陆羽** 品鉴过，列为江南名泉\n"
                     "3. **江南第一钟** - 重 **12.8吨** 的祥符禅钟，钟声浑厚洪亮，响彻山谷\n\n"
                     "**撞钟祈福：** 游客可参与撞钟活动，寓意'烦恼尽除、福慧增长'。",
                     "景点介绍", "祥符禅寺,历史,千年古刹,寺庙", 14),
                    ("五印坛城有什么特色？",
                     "**五印坛城** 位于香水海中央独立圆岛，四面环水，'小布达拉宫'之称。\n\n"
                     "**建筑特色：** 五层重檐楼宇，总高约30米，藏式碉楼风格，白墙红边金顶，"
                     "以西藏拉萨布达拉宫雪村大门为原型设计山门；"
                     "四门安置马宝、孔雀、共命鸟、象宝四尊青铜瑞兽（各高2.5米）。\n\n"
                     "**文化内涵：** '五印'代表五方五佛的五种手印，坛城是藏传佛教'曼陀罗道场'，"
                     "象征宇宙圆满；体现汉传佛教与藏传佛教的文化交融。\n\n"
                     "**特色体验：**\n"
                     "- 转经筒长廊：108个纯铜转经筒，顺时针转动寓意'福慧双增'\n"
                     "- 唐卡展厅：采用天然矿物颜料绘制，百年色彩鲜艳\n"
                     "- 登顶观景：俯瞰香水海、灵山梵宫与灵山大佛全景\n"
                     "- 藏香制作：需预约（10:00/14:00场）",
                     "景点介绍", "五印坛城,藏传,转经筒,坛城,藏式", 15),
                    ("灵山胜境的历史渊源是什么？",
                     "**灵山胜境的历史可追溯至1300多年前的唐代贞观年间。**\n\n"
                     "**玄奘法师与小灵山：** 唐贞观年间，玄奘法师西行取经归来，途经马山，"
                     "见此地'层峦丛翠，曲水净秀，山形酷似印度灵鹫山'，遂命名为'小灵山'，"
                     "并嘱大弟子窥基法师在此住持道场，兴建小灵山庵，奠定佛教根基。\n\n"
                     "**风水格局：** 背靠灵山主峰，面朝太湖三万顷碧波，"
                     "左右青龙白虎二山环抱，形成'前有照、后有靠、左右有抱'的风水格局。\n\n"
                     "**现代发展：** 1994年奠基，1997年大佛落成；2003年九龙灌浴建成；"
                     "2009年灵山梵宫正式开放，逐步形成集信仰、艺术、文化、旅游于一体的5A景区。",
                     "文化背景", "历史,渊源,来历,玄奘,起源,典故", 16),
                    ("灵山胜境有哪些祈福体验？",
                     "灵山胜境是佛教祈福圣地，有多种核心祈福体验：\n\n"
                     "1. **抱佛脚** - 登上灵山大佛216级登云道，在大佛脚下祈福，是最经典的祈福方式\n"
                     "2. **摸天下第一掌** - 触摸大佛右手等比复制品，寓意'沾福气、保平安'\n"
                     "3. **接九龙圣水** - 九龙灌浴演出结束后接取龙头流出的'圣水'，寓意吉祥安康\n"
                     "4. **撞祥符禅钟** - 在祥符禅寺参与撞钟，寓意'烦恼尽除、福慧增长'\n"
                     "5. **转五印坛城经筒** - 顺时针转动108个铜制转经筒，寓意'福慧双增'\n"
                     "6. **触摸佛足坛** - 触摸复刻的佛足印32种吉祥图案，寄托祈福心愿\n"
                     "7. **触摸百子弥勒肚皮** - 寓意'享一生福气'",
                     "文化背景", "祈福,抱佛脚,圣水,撞钟,转经筒,祈福体验", 17),
                    # ---- 餐饮住宿 ----
                    ("景区有什么吃的？",
                     "灵山胜境餐饮以 **佛门素斋** 为特色：\n\n"
                     "**1. 梵宫素斋自助（约50元/位）** - 清淡雅致，体验佛门饮食文化，菜品丰富\n"
                     "**2. 素面套餐（约35元/位）** - 景区内多个餐厅提供，价格实惠，口味清淡\n"
                     "**3. 灵山精舍素斋** - 禅意酒店内的素斋，环境优雅，菜品精致\n\n"
                     "**拈花湾小镇：**\n"
                     "- 香月花街各式禅意餐饮铺，提供江南小吃、禅茶等\n"
                     "- 无尽意斋、拈花堂提供免费禅茶品鉴\n\n"
                     "景区内饮食以素食为主，符合佛教文化氛围。",
                     "餐饮", "吃的,餐饮,素斋,素面,吃饭,食物", 18),
                    ("有住宿推荐吗？",
                     "灵山胜境周边住宿推荐：\n\n"
                     "**1. 灵山精舍（景区内）** - 含 **素斋与早课体验**，"
                     "体验'天人合一'的传统园林文化，适合深度感受佛教文化\n"
                     "**2. 拈花湾禅意小镇酒店群** - 紧邻景区，禅意风格，"
                     "适合喜爱小镇生活的游客，可体验夜间《禅行》灯光秀\n"
                     "**3. 马山镇周边酒店、民宿** - 价格从几百到上千元不等，选择丰富\n\n"
                     "建议提前预订，节假日期间房源紧张。",
                     "住宿", "住宿,酒店,民宿,精舍,住哪,住宿推荐", 19),
                    # ---- 交通 ----
                    ("景区停车方便吗？",
                     "灵山胜境景区设有大型停车场，**节假日高峰期建议提前1小时** 到达。\n\n"
                     "**交通方式：**\n"
                     "- 自驾：沿无锡太湖大道行驶，导航'灵山胜境'即可\n"
                     "- 公交：无锡市区多路公交直达，可查询'灵山'站\n"
                     "- 旅游大巴：景区有专线大巴服务\n\n"
                     "**景区内交通：** 建议购买 **网购联票（225元含观光车无限次）**，"
                     "或单独购买观光车票（40元/人），景区内步行距离较长。",
                     "交通", "停车,交通,自驾,公交,怎么去,路线,开车", 20),
                    # ---- 实用贴士 ----
                    ("最佳游览季节是什么时候？",
                     "**最佳季节：春秋（3-5月、9-11月）**\n\n"
                     "- **春季（3-5月）：** 樱花、桃花盛开，梵天花海格桑花绽放，气候宜人\n"
                     "- **秋季（9-11月）：** 祥符禅寺 **千年银杏金黄**，波斯菊再度盛开，景色绝美\n\n"
                     "**最佳时段：**\n"
                     "- 上午9点前入园避高峰，可从容欣赏每处景点\n"
                     "- 下午可观赏太湖日落，夕阳洒在灵山大佛上，'佛光普照'壮丽无比\n\n"
                     "**九龙灌浴表演：** 晴天时水幕与阳光交织出七彩佛光，效果最佳。",
                     "实用贴士", "季节,什么时候,最佳,最好,时间", 21),
                    ("游览灵山要注意什么？",
                     "灵山胜境游览实用贴士：\n\n"
                     "**穿着：** 步行较多，**建议穿运动鞋**；进入寺庙建议穿着素雅，避免过于鲜艳\n\n"
                     "**文明游览：**\n"
                     "- 景区为佛教文化场所，请保持安静，尊重宗教信仰\n"
                     "- 梵宫、佛教文化博览馆内禁止使用闪光灯\n"
                     "- 拈花堂内禁止大声喧哗，手机调至静音\n"
                     "- 梵天花海禁止采摘花卉、踩踏草坪\n\n"
                     "**携带物品：** 相机/手机、充电宝、防晒霜、雨伞\n\n"
                     "**导游服务：** 景区提供导游讲解服务，**300元起**，适合深度了解历史文化。",
                     "实用贴士", "注意,贴士,着装,建议,提示", 22),
                    # ---- 拈花湾 ----
                    ("拈花湾有什么好玩的？",
                     "**拈花湾禅意小镇** 是毗邻灵山胜境的禅意文化小镇，开放时间 **09:00-21:30**，\n"
                     "夜间比灵山主景区更有氛围感！\n\n"
                     "**核心景点：**\n"
                     "- **拈花广场：** 入口核心，'拈花微笑'雕塑，每日9:30举办禅意开园仪式\n"
                     "- **梵天花海：** 30000平方米花海，四季有花，拍照圣地\n"
                     "- **香月花街：** 800米禅意商业街，逛文创买禅茶，夜间灯笼氛围极佳\n"
                     "- **五灯湖：** 夜间《禅行》灯光秀（19:00/20:00），如梦如幻\n"
                     "- **拈花堂：** 免费禅坐、抄经、禅茶，静心体验\n"
                     "- **鹿鸣谷：** 静谧山林，适合漫步放松\n\n"
                     "**建议：** 下午3点后入拈花湾，白天赏花逛街，夜间看灯光秀。",
                     "景点介绍", "拈花湾,小镇,好玩,禅意小镇,拈花湾景点", 23),
                    # ---- 灵山文化 ----
                    ("百子戏弥勒有什么寓意？",
                     "**百子戏弥勒** 是灵山胜境内一处充满欢乐气息的青铜群雕，高3米、宽7.8米、重9吨。\n\n"
                     "弥勒佛是佛教中的 **未来佛**，象征'欢喜、包容、慈悲'。"
                     "弥勒佛呈卧姿，袒胸露腹、笑容憨厚可掬，尽显'大肚能容天下难容之事'的包容气度。\n\n"
                     "身上百名孩童形态各异、生动活泼，有的攀爬嬉戏，有的挠弥勒佛肚皮，"
                     "寓意 **'多子多福、家庭和睦、子孙满堂'**。\n\n"
                     "**祈福体验：** 触摸弥勒佛肚皮，寓意'摸弥勒肚皮，享一生福气'，"
                     "是景区内最受游客喜爱的祈福互动之一，亲子拍照定格温馨瞬间。",
                     "景点介绍", "百子戏弥勒,弥勒,寓意,百子,祈福", 24),
                    ("灵山梵宫是什么时候建的？",
                     "**灵山梵宫** 于 **2009年1月1日** 正式对外开放，是灵山胜境三期工程的核心建筑。\n\n"
                     "建设历程：2006年启动建设，历时约3年完工，荣获中国建筑工程最高奖——**鲁班奖**。\n\n"
                     "建筑面积达 **72000平方米**（约10个标准足球场大小），最高处66.5米，"
                     "整体造型以'莲花环抱'为设计理念，拥有五座错落分布的莲花圣塔。\n\n"
                     "自建成以来，先后举办了 **第二届、第四届世界佛教论坛**，"
                     "成为全球佛教文化交流的重要平台，被誉为'东方卢浮宫'。",
                     "景点介绍", "梵宫,什么时候,建造,历史,建设", 25),
                    ("你是谁？",
                     "我是 **灵山景区的智能助手小贞**，很高兴为您服务！🪷\n\n"
                     "请问您想了解关于灵山胜境的哪些信息呢？\n"
                     "我可以为您提供：景点介绍、路线规划、门票信息、演出时间、餐饮住宿等咨询服务。",
                     "其他", "你是谁,叫什么,小贞,介绍自己", 26),
                ]
                cur.executemany("""
                    INSERT INTO faqs (question, answer, category, keywords, sort_order)
                    VALUES (%s, %s, %s, %s, %s)
                """, faqs)
                print("[数据库] FAQ 数据写入完成, 共 %d 条" % len(faqs))

            # ===== 数字人默认形象 =====
            cur.execute("SELECT COUNT(*) AS cnt FROM digital_human_configs")
            if cur.fetchone()["cnt"] == 0:
                cur.execute(
                    """
                    INSERT INTO digital_human_configs
                    (name, voice_name, voice_style, appearance, clothing, cultural_style, keywords, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        "灵小佑",
                        "zh-CN-XiaoxiaoNeural",
                        "亲切、温柔、语速略快、适合导游讲解",
                        "年轻亲和的江南数字导游形象，表情自然，适合语音和口型同步展示",
                        "新中式导游服饰，莲花纹样、淡青与米白配色，呼应灵山佛教文化和太湖山水",
                        "禅意、江南、佛教文化、非遗纹样、太湖山水",
                        "灵山,导游,禅意,莲花,新中式,温柔女声,亲和,佛教文化,江南",
                    ),
                )
                print("[数据库] 数字人默认形象写入完成")

            # 可选：通过环境变量初始化管理员，避免代码内硬编码管理员密码
            if ADMIN_PHONE and ADMIN_PASSWORD:
                cur.execute("SELECT id FROM users WHERE phone = %s", (ADMIN_PHONE,))
                if not cur.fetchone():
                    import bcrypt
                    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt())
                    cur.execute(
                        "INSERT INTO users (phone, password, role) VALUES (%s, %s, 'admin')",
                        (ADMIN_PHONE, hashed.decode("utf-8")),
                    )
                    print("[数据库] 已根据 ADMIN_PHONE/ADMIN_PASSWORD 创建管理员账号")
                else:
                    cur.execute("UPDATE users SET role = 'admin' WHERE phone = %s", (ADMIN_PHONE,))

        conn.commit()
        print("[数据库] 初始数据写入完成")
    except Exception as e:
        conn.rollback()
        print(f"[数据库] 初始数据写入失败: {e}")
