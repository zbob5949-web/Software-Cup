from pathlib import Path

path = Path('app/database.py')
s = path.read_text(encoding='utf-8')
old = '''            cur.executemany(
                "INSERT INTO tickets (name, ticket_type, price, stock, status, description) VALUES (%s, %s, %s, %s, 'on_sale', %s)",
                products)
    except Exception as exc:'''
new = '''            cur.executemany(
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
    except Exception as exc:'''
if old not in s: raise RuntimeError('sqlite ticket seed block not found')
path.write_text(s.replace(old, new, 1), encoding='utf-8')
