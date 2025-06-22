import streamlit as st
import duckdb
import pandas as pd
import hashlib

# --- データベース関数 ---

def init_db(db_path='books.db'):
    """データベース接続を初期化し、テーブルが存在しない場合は作成する。"""
    db = duckdb.connect(database=db_path, read_only=False)
    db.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER,
            title TEXT NOT NULL,
            series TEXT,
            author TEXT,
            publisher TEXT
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    return db

def get_next_id(db):
    """新しい書籍の次の利用可能なIDを取得する。"""
    result = db.execute("SELECT MAX(id) FROM books").fetchone()
    return (result[0] or 0) + 1

def get_sorted_values(db, column_name):
    """列から一意な値をアルファベット順にソートして取得する。"""
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL ORDER BY {column_name} ASC"
    result = db.execute(query).fetchall()
    return [r[0] for r in result]

def insert_book(db, title, series, author, publisher):
    """データベースに新しい書籍を挿入する。"""
    new_id = get_next_id(db)
    db.execute(
        "INSERT INTO books (id, title, series, author, publisher) VALUES (?, ?, ?, ?, ?)",
        (new_id, title, series if series else None, author if author else None, publisher if publisher else None),
    )
    return new_id
    

def search_books(db, title=None, series=None, author=None, publisher=None):
    """指定された条件に基づいて書籍を検索する。"""
    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if title:
        query += " AND title LIKE ?"
        params.append(f"%{title}%")

    if series:
        query += " AND series LIKE ?"
        params.append(f"%{series}%")

    if author:
        query += " AND author LIKE ?"
        params.append(f"%{author}%")

    if publisher:
        query += " AND publisher LIKE ?"
        params.append(f"%{publisher}%")

    return db.execute(query, params).fetchdf()

def get_book_by_id(db, book_id):
    """IDによって書籍のデータを取得する。"""
    return db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

def update_book(db, book_id, title, series, author, publisher):
    """データベース内の書籍データを更新する。"""
    db.execute("UPDATE books SET title = ?, series = ?, author = ?, publisher = ? WHERE id = ?",
               (title, series, author, publisher, book_id))

def delete_book(db, book_id):
    """IDでデータベースから書籍を削除する。"""
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))

def get_all_books(db):
    """データベースからすべての書籍を取得する（選択用）。"""
    return db.execute("SELECT id, title FROM books").fetchall()

def export_books_to_csv(db):
    """すべての書籍をCSV文字列でエクスポートする。"""
    data = db.execute("SELECT * FROM books").fetchdf()
    return data.to_csv(index=False)

def import_books_from_csv(db, csv_file):
    """CSVファイルからデータベースに書籍をインポートする。"""
    try:
        df = pd.read_csv(csv_file)
        if "title" not in df.columns:
            raise ValueError("CSV file does not contain the 'title' column.")
        for column in ["series", "author", "publisher"]:
            if column not in df.columns:
                df[column] = None
        max_id = db.execute("SELECT MAX(id) FROM books").fetchone()[0] or 0
        df["id"] = range(max_id + 1, max_id + 1 + len(df))
        data_to_insert = df[["id", "title", "series", "author", "publisher"]].to_records(index=False).tolist()
        db.executemany("INSERT INTO books (id, title, series, author, publisher) VALUES (?, ?, ?, ?, ?)", data_to_insert)
        return True
    except Exception as e:
        raise e

# --- ユーザー認証関数 ---

def hash_password(password):
    """SHA-256を使用してパスワードをハッシュ化する。"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(db, username, password):
    """ハッシュ化されたパスワードで新しいユーザーを作成する。"""
    password_hash = hash_password(password)
    try:
        max_id = db.execute("SELECT MAX(id) FROM users").fetchone()[0] or 0
        new_id = max_id + 1
        db.execute("INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)", (new_id, username, password_hash))
        return True
    except Exception:
        return False

def verify_user(db, username, password):
    """ユーザーの認証情報を検証する。"""
    password_hash = hash_password(password)
    result = db.execute("SELECT username FROM users WHERE username = ? AND password_hash = ?", 
                       (username, password_hash)).fetchone()
    return result is not None

def is_authenticated():
    """現在のセッションでユーザーが認証されているかどうかをチェックする。"""
    return st.session_state.get("authenticated", False)

def get_current_user():
    """現在認証されているユーザーを取得する。"""
    return st.session_state.get("username", None)

# --- Streamlit UI関数 ---

def ui_register_book(db):
    """新しい書籍を登録するためのUI。"""
    st.header("新しい書籍を登録")
    
    if not is_authenticated():
        st.warning("書籍を登録するにはログインが必要です")
        return

    title = st.text_input("書籍名 (必須)", max_chars=255)

    series_options = [""] + get_sorted_values(db, "series")
    selected_series = st.selectbox("既存のシリーズから選択(任意)", series_options)
    new_series = st.text_input("またはシリーズを入力")
    series = new_series.strip() if new_series.strip() else selected_series

    author_options = [""] + get_sorted_values(db, "author")
    selected_author = st.selectbox("既存の著者名から選択 (任意)", author_options)
    new_author = st.text_input("または著者名を入力")
    author = new_author.strip() if new_author.strip() else selected_author

    publisher_options = [""] + get_sorted_values(db, "publisher")
    selected_publisher = st.selectbox("既存の出版社から選択 (任意)", publisher_options)
    new_publisher = st.text_input("または出版社を入力")
    publisher = new_publisher.strip() if new_publisher.strip() else selected_publisher

    if st.button("登録"):
        if title.strip():
            insert_book(db, title, series, author, publisher)
            st.success("Book registered successfully!")
        else:
            st.error("書籍名は必須です!!")

def ui_search_books(db):
    """書籍検索用のUI。"""
    st.header("検索")

    title = st.text_input("書籍名で検索")
    series = st.text_input("シリーズで検索")
    author = st.text_input("著者名で検索")
    publisher = st.text_input("出版社で検索")

    results = search_books(db, title, series, author, publisher)
    st.write(results)

def ui_edit_book(db):
    """既存の書籍を編集するためのUI。"""
    st.header("書籍編集")

    if not is_authenticated():
        st.warning("書籍編集を行うにはログインが必要です。")
        return

    books = get_all_books(db)
    book_options = {f"{id}: {title}": id for id, title in books}
    selected = st.selectbox("編集する書籍を選択(IDもしくは書籍名の部分一致)", [""] + list(book_options.keys()))

    if selected:
        book_id = book_options[selected]
        book_data = get_book_by_id(db, book_id)

        title = st.text_input("書籍名", value=book_data[1], max_chars=255)
        series = st.text_input("シリーズ", value=book_data[2])
        author = st.text_input("著者名", value=book_data[3])
        publisher = st.text_input("出版社", value=book_data[4])

        if st.button("更新"):
            update_book(db, book_id, title, series, author, publisher)
            st.success("書籍を更新しました!!")

def ui_delete_book(db):
    """書籍削除用のUI。"""
    st.header("書籍削除")

    if not is_authenticated():
        st.warning("書籍削除を行うにはログインが必要です。")
        return

    books = get_all_books(db)
    if books:
        book_options = {f"{id}: {title}": id for id, title in books}
        selected = st.selectbox("削除する書籍を選択", [""] + list(book_options.keys()))

        if selected:
            book_id = book_options[selected]
            book_data = get_book_by_id(db, book_id)

            st.write(f"書籍名:{book_data[1]}")
            st.write(f"シリーズ:{book_data[2]}")
            st.write(f"著者名:{book_data[3]}")
            st.write(f"出版社:{book_data[4]}")

            if st.button("削除"):
                try:
                    delete_book(db, book_id)
                    st.success(f"ID {book_id} の書籍を削除しました")
                except Exception as e:
                    st.error(f"An error occurred while deleting the book: {e}")
    else:
        st.info("削除する書籍がありません")

def ui_export_csv(db):
    """書籍をCSVにエクスポートするためのUI。"""
    st.header("CSV形式でエクスポート")
    csv = export_books_to_csv(db)
    st.download_button(label="ダウンロード", data=csv, file_name="books.csv", mime="text/csv")

def ui_import_csv(db):
    """CSVから書籍をインポートするためのUI。"""
    st.header("CSVファイルをインポート")
    st.markdown('''
        以下の4つの列をもつCSVファイル（UTF-8エンコーディング）をアップロードします。

        「title」「series」「author」「publisher」

        重複があっても追加されますのでご注意ください。
    ''')

    uploaded_file = st.file_uploader("ファイルアップロード", type=["csv"])

    if uploaded_file is not None:
        try:
            if import_books_from_csv(db, uploaded_file):
                st.success("インポート終了")
            else:
                st.error("インポートに失敗しました。")
        except Exception as e:
            st.error(f"An error occurred while importing the CSV: {e}")

def ui_login(db):
    """ユーザーログイン用のUI。"""
    st.header("ログイン")
    
    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("ログイン"):
            if username and password:
                if verify_user(db, username, password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.success("ログインしました")
                    st.rerun()
                else:
                    st.error("ユーザー名またはパスワードが間違っています")
            else:
                st.error("ユーザー名とパスワードを入力してください")
    
    with col2:
        if st.button("新規ユーザー登録"):
            if username and password:
                if create_user(db, username, password):
                    st.success("ユーザーを登録しました。ログインしてください。")
                else:
                    st.error("ユーザー名が既に存在するか、登録に失敗しました")
            else:
                st.error("ユーザー名とパスワードを入力してください")

def ui_logout():
    """ユーザーログアウト用のUI。"""
    if st.sidebar.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.rerun()

# --- メインアプリ ---

def main():
    st.set_page_config(
        page_title="Soogie's books",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    db = init_db()

    # セッションステートを初期化
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = None

    # ログイン状態とログアウトボタンを表示
    if is_authenticated():
        st.sidebar.success(f"ログイン中: {get_current_user()}")
        ui_logout()
    
    menu = ["ログイン", "検索", "登録", "編集", "削除", "CSVエクスポート", "CSVインポート"]
    choice = st.sidebar.selectbox("Menu", menu, index=1)

    if choice == "ログイン":
        ui_login(db)
    elif choice == "検索":
        ui_search_books(db)
    elif choice == "登録":
        ui_register_book(db)
    elif choice == "編集":
        ui_edit_book(db)
    elif choice == "削除":
        ui_delete_book(db)
    elif choice == "CSVエクスポート":
        ui_export_csv(db)
    elif choice == "CSVインポート":
        ui_import_csv(db)

    # Close the connection when the app is done
    # db.close() # Don't need to explicity close connection with duckdb

if __name__ == '__main__':
    main()
