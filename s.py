#!/usr/bin/env python3
from argparse import SUPPRESS, ArgumentParser, RawDescriptionHelpFormatter
from datetime import date, timedelta
from os import system
from pydoc import pager
from sqlite3 import Row, connect

DB_PATH = "/Users/kangmin/.local/share/s/db"
EPI_ROOT_DIR = "/Users/kangmin/EPIJudge/epi_judge_cpp"
EXT = "cc"
DESC = '''
scoring:
   0: Total blackout.
   1: Incorrect, but felt familiar after seeing answer.
   2: Incorrect, but seemed easy to remember after seeing answer.
   3: Correct, but required significant effort to recall.
   4: Correct, after some hesitation.
   5: Correct, with perfect recall.
'''

def print_problems(rows):
    output = []
    for id, ti, dt in rows:
        dt = date.fromisoformat(dt).strftime("%-m/%d") if dt else ""
        output.append(f"{id // 100:>3}.{id % 100:02d}  {ti:<66}{dt:>5}")
    pager("\n".join(output))

def edit_files(cursor, id):
    cursor.execute("select files from problems where id = ?", (id,))
    files = " ".join(f"{EPI_ROOT_DIR}/{basename}.{EXT}"
                     for basename in cursor.fetchone()[0].split(" "))
    system(f"(cd {EPI_ROOT_DIR} && git restore {files})")
    system(f"vi -p '+cd {EPI_ROOT_DIR}' "
           "'+nn <leader>t :w \| !make<cr>' "
           f"'+nn <leader>r :e {EPI_ROOT_DIR}_solutions/%<cr>' "
           f"{files}")

def sm2(q, n, ef, i):
    return (0 if q < 3 else n + 1,
            max(ef + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02), 1.3),
            1 if q < 3 else 1 if n == 0 else 6 if n == 1 else round(i * ef))

def update_problem(cursor, id, q):
    cursor.execute("select date, n, ef, i from problems where id = ?", (id,))
    dt, n, ef, i = cursor.fetchone()
    dt = max(date.fromisoformat(dt) if dt else date.today(), date.today())
    n, ef, i = sm2(q, n, ef, i)
    dt += timedelta(days=i)
    cursor.execute("""update problems set date = ?, n = ?, ef = ?, i = ?
                      where id = ?""", (dt, n, ef, i, id))

if __name__ == "__main__":
    con = connect(DB_PATH)
    con.row_factory = Row
    cursor = con.cursor()
    parser = ArgumentParser(usage="%(prog)s [-h] [id] [score]",
                            formatter_class=RawDescriptionHelpFormatter,
                            description=DESC)
    cursor.execute("""select id, title, date from problems
                      where date <= date('now', 'localtime') or date is null
                      order by date nulls last, id""")
    rows = cursor.fetchall()
    parser.add_argument("id", type=int, nargs="?", help=SUPPRESS,
                        choices=tuple(row['id'] for row in rows))
    parser.add_argument("score", type=int, nargs="?", help=SUPPRESS,
                        choices=range(6))
    args = parser.parse_args()
    if args.id and args.score:
        update_problem(cursor, args.id, args.score)
    elif args.id:
        edit_files(cursor, args.id)
    else:
        print_problems(rows)
    con.commit()
    con.close()
