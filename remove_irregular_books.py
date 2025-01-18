import duckdb

# データベースに接続
db = duckdb.connect("books.db")

# 削除クエリの実行
db.execute("DELETE FROM books WHERE id IS NULL")

# 確認
remaining = db.execute("SELECT * FROM books WHERE id IS NULL").fetchall()
if not remaining:
    print("All records with NULL ID have been deleted.")
else:
    print("Some records still remain:", remaining)

# 接続を閉じる
db.close()
