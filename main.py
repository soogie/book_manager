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

# Helper function to fetch distinct values for dropdown
def get_distinct_values(column_name):
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL"
    result = db.execute(query).fetchall()
    return [r[0] for r in result]

# Fetch distinct values for dropdown, sorted in alphabetical order
def get_sorted_values(column_name):
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL ORDER BY {column_name} ASC"
    result = db.execute(query).fetchall()
    return [r[0] for r in result]


def import_csv():
    st.header("Import Books from CSV")

    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(uploaded_file)

            # Check if required column "title" exists
            if "title" not in df.columns:
                st.error("The CSV must contain at least a 'title' column.")
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
            st.success("Books imported successfully!")
        except Exception as e:
            st.error(f"An error occurred while importing the CSV: {e}")


# UI
def main():
    st.title("Book Management Web App")

    menu = ["Register Book", "Search Books", "Edit Book", "Delete Book", "Export to CSV", "Import from CSV"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register Book":
        st.header("Register a New Book")

        title = st.text_input("Book Title (Required)", max_chars=255)

        # Series input
        series_options = [""] + get_sorted_values("series")
        selected_series = st.selectbox("Series Name (Optional)", series_options)
        new_series = st.text_input("Or Enter a New Series Name (Optional)")
        series = new_series.strip() if new_series.strip() else selected_series

        # Author input
        author_options = [""] + get_sorted_values("author")
        selected_author = st.selectbox("Author Name (Optional)", author_options)
        new_author = st.text_input("Or Enter a New Author Name (Optional)")
        author = new_author.strip() if new_author.strip() else selected_author

        # Publisher input
        publisher_options = [""] + get_sorted_values("publisher")
        selected_publisher = st.selectbox("Publisher Name (Optional)", publisher_options)
        new_publisher = st.text_input("Or Enter a New Publisher Name (Optional)")
        publisher = new_publisher.strip() if new_publisher.strip() else selected_publisher

        if st.button("Register"):
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
                st.error("Book title is required!")


    elif choice == "Search Books":
        st.header("Search Books")

        title = st.text_input("Search by Title")
        series = st.text_input("Search by Series")
        author = st.text_input("Search by Author")
        publisher = st.text_input("Search by Publisher")

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

    elif choice == "Edit Book":
        st.header("Edit Book")

        books = db.execute("SELECT id, title FROM books").fetchall()
        book_options = {f"{id}: {title}": id for id, title in books}
        selected = st.selectbox("Select a Book to Edit", [""] + list(book_options.keys()))

        if selected:
            book_id = book_options[selected]
            book_data = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

            title = st.text_input("Book Title", value=book_data[1], max_chars=255)
            series = st.text_input("Series", value=book_data[2])
            author = st.text_input("Author", value=book_data[3])
            publisher = st.text_input("Publisher", value=book_data[4])

            if st.button("Update"):
                db.execute("UPDATE books SET title = ?, series = ?, author = ?, publisher = ? WHERE id = ?",
                           (title, series, author, publisher, book_id))
                st.success("Book updated successfully!")

    elif choice == "Delete Book":
        st.header("Delete Book")

        # Fetch all books for selection
        books = db.execute("SELECT id, title FROM books").fetchall()
        if books:
            book_options = {f"{id}: {title}": id for id, title in books}
            selected = st.selectbox("Select a Book to Delete", [""] + list(book_options.keys()))

            if selected:
                book_id = book_options[selected]

                # Confirm deletion
                if st.button("Delete"):
                    try:
                        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                        st.success(f"Book with ID {book_id} deleted successfully!")
                    except Exception as e:
                        st.error(f"An error occurred while deleting the book: {e}")
        else:
            st.info("No books available to delete.")

    elif choice == "Export to CSV":
        st.header("Export Books to CSV")

        data = db.execute("SELECT * FROM books").fetchdf()
        csv = data.to_csv(index=False)
        st.download_button(label="Download CSV", data=csv, file_name="books.csv", mime="text/csv")
    
    elif choice == "Import from CSV":
        import_csv()

if __name__ == '__main__':
    main()
