import pytest
import duckdb
import pandas as pd
from main import (
    init_db,
    get_next_id,
    get_sorted_values,
    insert_book,
    search_books,
    get_book_by_id,
    update_book,
    delete_book,
    get_all_books,
    export_books_to_csv,
    import_books_from_csv,
)
import tempfile
import os

@pytest.fixture(scope="function")
def db():
    """
    Fixture to create a temporary database for each test and close it afterwards.
    """
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db_path = temp_db_file.name
    temp_db_file.close()
    
    db_conn = init_db(temp_db_path)
    
    yield db_conn
    
    db_conn.close()
    os.unlink(temp_db_path)
    

def test_init_db(db):
    """Test if the database is initialized correctly."""
    result = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'").fetchone()
    assert result is not None
    assert result[0] == "books"


def test_get_next_id(db):
    """Test if get_next_id function works correctly."""
    assert get_next_id(db) == 1
    db.execute("INSERT INTO books (id, title) VALUES (1, 'Book 1')")
    assert get_next_id(db) == 2
    db.execute("INSERT INTO books (id, title) VALUES (5, 'Book 5')")
    assert get_next_id(db) == 6


def test_get_sorted_values(db):
    """Test if get_sorted_values function works correctly."""
    db.execute("INSERT INTO books (id, title, author) VALUES (1, 'Book 1', 'Author B')")
    db.execute("INSERT INTO books (id, title, author) VALUES (2, 'Book 2', 'Author A')")
    db.execute("INSERT INTO books (id, title, author) VALUES (3, 'Book 3', 'Author C')")
    assert get_sorted_values(db, "author") == ["Author A", "Author B", "Author C"]
    assert get_sorted_values(db, "publisher") == []


def test_insert_book(db):
    """Test if insert_book function works correctly."""
    new_id = insert_book(db, "Test Book", "Test Series", "Test Author", "Test Publisher")
    assert new_id == 1
    result = db.execute("SELECT * FROM books WHERE id=1").fetchone()
    assert result == (1, "Test Book", "Test Series", "Test Author", "Test Publisher")

    new_id = insert_book(db, "Test Book2", None, None, None)
    assert new_id == 2
    result = db.execute("SELECT * FROM books WHERE id=2").fetchone()
    assert result == (2, "Test Book2", None, None, None)


def test_search_books(db):
    """Test if search_books function works correctly."""
    db.execute("INSERT INTO books (id, title, series, author, publisher) VALUES (1, 'Book 1', 'Series A', 'Author A', 'Publisher X')")
    db.execute("INSERT INTO books (id, title, series, author, publisher) VALUES (2, 'Book 2', 'Series B', 'Author B', 'Publisher Y')")
    db.execute("INSERT INTO books (id, title, series, author, publisher) VALUES (3, 'Different Book', 'Series A', 'Author C', 'Publisher Z')")

    results = search_books(db, title="Book")
    assert len(results) == 2

    results = search_books(db, series="Series A")
    assert len(results) == 2

    results = search_books(db, author="Author B")
    assert len(results) == 1

    results = search_books(db, publisher="Publisher Z")
    assert len(results) == 1

    results = search_books(db, title="Book", series="Series A")
    assert len(results) == 1

    results = search_books(db, title="Nonexistent")
    assert len(results) == 0

def test_get_book_by_id(db):
    """Test if get_book_by_id function works correctly."""
    db.execute("INSERT INTO books (id, title, series, author, publisher) VALUES (1, 'Book 1', 'Series A', 'Author A', 'Publisher X')")
    book = get_book_by_id(db, 1)
    assert book == (1, "Book 1", "Series A", "Author A", "Publisher X")
    assert get_book_by_id(db, 99) is None

def test_update_book(db):
    """Test if update_book function works correctly."""
    db.execute("INSERT INTO books (id, title, series, author, publisher) VALUES (1, 'Book 1', 'Series A', 'Author A', 'Publisher X')")
    update_book(db, 1, "Updated Book", "Updated Series", "Updated Author", "Updated Publisher")
    book = get_book_by_id(db, 1)
    assert book == (1, "Updated Book", "Updated Series", "Updated Author", "Updated Publisher")

def test_delete_book(db):
    """Test if delete_book function works correctly."""
    db.execute("INSERT INTO books (id, title) VALUES (1, 'Book 1')")
    delete_book(db, 1)
    result = db.execute("SELECT * FROM books WHERE id=1").fetchone()
    assert result is None

def test_get_all_books(db):
    """Test if get_all_books function works correctly."""
    db.execute("INSERT INTO books (id, title) VALUES (1, 'Book 1')")
    db.execute("INSERT INTO books (id, title) VALUES (2, 'Book 2')")
    books = get_all_books(db)
    assert len(books) == 2
    assert (1,"Book 1") in books
    assert (2, "Book 2") in books


def test_export_books_to_csv(db):
    """Test if export_books_to_csv function works correctly."""
    db.execute("INSERT INTO books (id, title, series, author, publisher) VALUES (1, 'Book 1', 'Series A', 'Author A', 'Publisher X')")
    csv_string = export_books_to_csv(db)
    assert "id,title,series,author,publisher" in csv_string
    assert "1,Book 1,Series A,Author A,Publisher X" in csv_string

def test_import_books_from_csv(db):
    """Test if import_books_from_csv function works correctly."""
    # Create a sample CSV file
    csv_data = "title,series,author,publisher\nBook 1,Series A,Author A,Publisher X\nBook 2,,Author B,"
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_csv_file:
        temp_csv_file.write(csv_data)
        temp_csv_path = temp_csv_file.name

    # Import books from the temporary CSV file
    import_books_from_csv(db, temp_csv_path)

    # Check if the books were imported correctly
    books = db.execute("SELECT * FROM books").fetchall()
    assert len(books) == 2
    assert books[0] == (1, "Book 1", "Series A", "Author A", "Publisher X")
    assert books[1] == (2, "Book 2", None, "Author B", None)
    
    os.unlink(temp_csv_path)

def test_import_books_from_csv_with_invalid_format(db):
    """Test if import_books_from_csv function works correctly."""
    # Create a sample CSV file
    csv_data = "name,series,author,publisher\nBook 1,Series A,Author A,Publisher X\nBook 2,,Author B,"
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_csv_file:
        temp_csv_file.write(csv_data)
        temp_csv_path = temp_csv_file.name

    with pytest.raises(ValueError):
        import_books_from_csv(db, temp_csv_path)
        
    os.unlink(temp_csv_path)
