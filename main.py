import streamlit as st
import duckdb
import pandas as pd

# Initialize the database connection
db = duckdb.connect(database='books.db', read_only=False)

# Create table if not exists
db.execute('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER,
    title TEXT NOT NULL,
    series TEXT,
    author TEXT,
    publisher TEXT
)
''')


# Helper function to generate a new ID
def get_next_id():
    result = db.execute("SELECT MAX(id) FROM books").fetchone()
    return (result[0] or 0) + 1

# Fetch distinct values for dropdown, sorted in alphabetical order
def get_sorted_values(column_name):
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL ORDER BY {column_name} ASC"
    result = db.execute(query).fetchall()
    return [r[0] for r in result]


def import_csv():
    st.header("CSVファイルをインポート")
    st.markdown('''
    
        以下の4つの列をもつCSVファイル（UTF-8エンコーディング）をアップロードします。

        「title」「series」「author」「publisher」

        重複があっても追加されますのでご注意ください。

    ''')

    uploaded_file = st.file_uploader("ファイルアップロード", type=["csv"])

    if uploaded_file is not None:
        try:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(uploaded_file)

            # Check if required column "title" exists
            if "title" not in df.columns:
                st.error("CSVファイルに'title'列がありません")
                return

            # Fill missing optional columns with None
            for column in ["series", "author", "publisher"]:
                if column not in df.columns:
                    df[column] = None

            # Assign new IDs to each row
            max_id = db.execute("SELECT MAX(id) FROM books").fetchone()[0] or 0
            df["id"] = range(max_id + 1, max_id + 1 + len(df))

            # Convert DataFrame to a list of tuples
            data_to_insert = df[["id", "title", "series", "author", "publisher"]].to_records(index=False).tolist()

            # Insert data into the database
            db.executemany(
                "INSERT INTO books (id, title, series, author, publisher) VALUES (?, ?, ?, ?, ?)",
                data_to_insert
            )
            st.success("インポート終了")
        except Exception as e:
            st.error(f"An error occurred while importing the CSV: {e}")


# UI
def main():
    st.title("Soogie's books")

    menu = ["登録", "検索", "編集", "削除", "CSVエクスポート", "CSVインポート"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "登録":
        st.header("新しい書籍を登録")

        title = st.text_input("書籍名 (必須)", max_chars=255)

        # Series input
        series_options = [""] + get_sorted_values("series")
        selected_series = st.selectbox("既存のシリーズから選択(任意)", series_options)
        new_series = st.text_input("またはシリーズを入力")
        series = new_series.strip() if new_series.strip() else selected_series

        # Author input
        author_options = [""] + get_sorted_values("author")
        selected_author = st.selectbox("既存の著者名から選択 (任意)", author_options)
        new_author = st.text_input("または著者名を入力")
        author = new_author.strip() if new_author.strip() else selected_author

        # Publisher input
        publisher_options = [""] + get_sorted_values("publisher")
        selected_publisher = st.selectbox("既存の出版社から選択 (任意)", publisher_options)
        new_publisher = st.text_input("または出版社を入力")
        publisher = new_publisher.strip() if new_publisher.strip() else selected_publisher

        if st.button("登録"):
            if title.strip():
                # Generate the next ID
                new_id = get_next_id()

                # Insert into the database
                db.execute(
                    "INSERT INTO books (id, title, series, author, publisher) VALUES (?, ?, ?, ?, ?)",
                    (new_id, title, series if series else None, author if author else None, publisher if publisher else None),
                )
                st.success("Book registered successfully!")
            else:
                st.error("書籍名は必須です!!")


    elif choice == "検索":
        st.header("検索")

        title = st.text_input("書籍名で検索")
        series = st.text_input("シリーズで検索")
        author = st.text_input("著者名で検索")
        publisher = st.text_input("出版社で検索")

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

        results = db.execute(query, params).fetchdf()
        st.write(results)

    elif choice == "編集":
        st.header("書籍編集")

        books = db.execute("SELECT id, title FROM books").fetchall()
        book_options = {f"{id}: {title}": id for id, title in books}
        selected = st.selectbox("Select a Book to Edit", [""] + list(book_options.keys()))

        if selected:
            book_id = book_options[selected]
            book_data = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

            title = st.text_input("書籍名", value=book_data[1], max_chars=255)
            series = st.text_input("シリーズ", value=book_data[2])
            author = st.text_input("著者名", value=book_data[3])
            publisher = st.text_input("出版社", value=book_data[4])

            if st.button("更新"):
                db.execute("UPDATE books SET title = ?, series = ?, author = ?, publisher = ? WHERE id = ?",
                           (title, series, author, publisher, book_id))
                st.success("書籍を更新しました!!")

    elif choice == "削除":
        st.header("書籍削除")

        # Fetch all books for selection
        books = db.execute("SELECT id, title FROM books").fetchall()
        if books:
            book_options = {f"{id}: {title}": id for id, title in books}
            selected = st.selectbox("Select a Book to Delete", [""] + list(book_options.keys()))

            if selected:
                book_id = book_options[selected]

                # Confirm deletion
                if st.button("削除"):
                    try:
                        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                        st.success(f"ID {book_id} の書籍を削除しました")
                    except Exception as e:
                        st.error(f"An error occurred while deleting the book: {e}")
        else:
            st.info("削除する書籍がありません")

    elif choice == "CSVエクスポート":
        st.header("CSV形式でエクスポート")

        data = db.execute("SELECT * FROM books").fetchdf()
        csv = data.to_csv(index=False)
        st.download_button(label="ダウンロード", data=csv, file_name="books.csv", mime="text/csv")
    
    elif choice == "CSVインポート":
        import_csv()

if __name__ == '__main__':
    main()
