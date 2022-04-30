#!/usr/bin/env python3
from argparse import ArgumentParser, RawDescriptionHelpFormatter, SUPPRESS
from datetime import date, timedelta
from os import getlogin, system
from pydoc import pager
from sqlite3 import Row, connect

USER = getlogin()
# Assume project root and EPIJudge folders are under $HOME.
DB_PATH = f"/Users/{USER}/s/s.db"
EPI_ROOT_DIR = f"/Users/{USER}/EPIJudge/epi_judge_python/"
EXT = ".py"
# EPI_ROOT_DIR = f"/Users/{USER}/EPIJudge/epi_judge_cpp/"
# EXT = ".cc"
DESC = '''
scoring:
   0: Total blackout.
   1: Incorrect, but felt familiar after seeing answer.
   2: Incorrect, but seemed easy to remember after seeing answer.
   3: Correct, but required significant effort to recall.
   4: Correct, after some hesitation.
   5: Correct, with perfect recall.
'''

def print_problems(cursor):
    output = []
    cursor.execute("""select * from problems
                      where date <= date('now', 'localtime') or date is null
                      order by date nulls last, id""")
    for row in cursor.fetchall():
        d = date.fromisoformat(row['date']).strftime("%-m/%d") if row['date'] else ""
        output.append("{:>3}.{:02d}  {:<66}{:>5}".format(
            row['id'] // 100, row['id'] % 100, row['title'], d))
    pager("\n".join(output))

def edit_files(cursor, id):
    cursor.execute("select files from problems where id = ?", (id,))
    files = " ".join(EPI_ROOT_DIR + basename + EXT
                     for basename in tuple(cursor.fetchone())[0].split(" "))
    system("(cd {} && git restore {})".format(EPI_ROOT_DIR, files))
    system("vi -p '+cd {}' '+nn ,t :w \| !make <cr>' {}".format(EPI_ROOT_DIR, files))

def sm2(q, n, ef, i):
    i, n = (1, 0) if q < 3 else (1 if n == 0 else 6 if n == 1 else round(i * ef), n + 1)
    return (n, max(ef + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02), 1.3), i)

def update_problem(cursor, connection, id, q):
    cursor.execute("select * from problems where id = ?", (id,))
    row = cursor.fetchone()
    d = date.fromisoformat(row['date']) if row['date'] else date.today()
    d = max(d, date.today())
    n, ef, i = sm2(q, *row[-3:])
    d += timedelta(days=i)
    cursor.execute("""update problems set date = ?, n = ?, ef = ?, i = ?
                      where id = ?""", (d, n, ef, i, id))
    connection.commit()

if __name__ == "__main__":
    connection = connect(DB_PATH)
    connection.row_factory = Row
    cursor = connection.cursor()
    parser = ArgumentParser(usage="%(prog)s [-h] [id] [score]",
                            formatter_class=RawDescriptionHelpFormatter,
                            description=DESC)
    cursor.execute("""select id from problems
                      where date <= date('now', 'localtime') or date is null
                      order by date nulls last, id""")
    parser.add_argument("id", type=int, nargs="?", help=SUPPRESS,
                        choices=tuple(row['id'] for row in cursor.fetchall()))
    parser.add_argument("score", type=int, nargs="?", help=SUPPRESS,
                        choices=range(6))
    args = parser.parse_args()
    if args.id and args.score:
        update_problem(cursor, connection, args.id, args.score)
    elif args.id:
        edit_files(cursor, args.id)
    else:
        print_problems(cursor)
    connection.close()
