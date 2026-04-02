import mysql.connector
from mysql.connector import Error
from datetime import date, timedelta

DB_CONFIG = {
    'host': 'localhost',
    'database': 'LibraryDB',
    'user': 'library_user',
    'password': 'library_pass123'
}

def create_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Подключение к базе данных успешно установлено")
            return connection
    except Error as e:
        print(f"Ошибка подключения: {e}")
        return None

def show_all_books(connection):
    cursor = connection.cursor()
    
    query = """
    SELECT 
        b.book_id,
        b.title,
        a.first_name,
        a.last_name,
        b.genre,
        b.total_copies,
        b.available_copies
    FROM Books b
    INNER JOIN Authors a ON b.author_id = a.author_id
    ORDER BY b.book_id
    """
    
    try:
        cursor.execute(query)
        books = cursor.fetchall()
        
        if not books:
            print("\nВ библиотеке пока нет книг")
            return
        
        print("\n" + "=" * 95)
        print(f"{'ID':<4} | {'Название':<30} | {'Автор':<25} | {'Жанр':<18} | {'Всего':<5} | {'Доступно':<8}")
        print("-" * 95)
        
        for book in books:
            author_full = f"{book[2]} {book[3]}"
            print(f"{book[0]:<4} | {book[1]:<30} | {author_full:<25} | {book[4]:<18} | {book[5]:<5} | {book[6]:<8}")
        
        print("=" * 95)
        
    except Error as e:
        print(f"Ошибка при выполнении запроса: {e}")
    finally:
        cursor.close()

def show_available_books(connection):
    cursor = connection.cursor()
    
    query = """
    SELECT b.book_id, b.title, a.first_name, a.last_name, b.available_copies
    FROM Books b
    INNER JOIN Authors a ON b.author_id = a.author_id
    WHERE b.available_copies > 0
    """
    
    try:
        cursor.execute(query)
        books = cursor.fetchall()
        
        print("\nКниги в наличии")
        for book in books:
            print(f"ID: {book[0]} | {book[1]} ({book[2]} {book[3]}) | Доступно: {book[4]}")
            
    except Error as e:
        print(f"Ошибка: {e}")
    finally:
        cursor.close()

def show_all_readers(connection):
    cursor = connection.cursor()
    
    query = "SELECT reader_id, first_name, last_name, email, phone FROM Readers"
    
    try:
        cursor.execute(query)
        readers = cursor.fetchall()
        
        if not readers:
            print("\nНет зарегистрированных читателей")
            return
        
        print("\n" + "=" * 70)
        print(f"{'ID':<4} | {'Имя':<15} | {'Фамилия':<15} | {'Email':<20} | {'Телефон':<12}")
        print("-" * 70)
        
        for reader in readers:
            print(f"{reader[0]:<4} | {reader[1]:<15} | {reader[2]:<15} | {reader[3]:<20} | {reader[4]:<12}")
        
        print("=" * 70)
        
    except Error as e:
        print(f"Ошибка: {e}")
    finally:
        cursor.close()

def add_new_reader(connection):
    print("\nДобавление нового читателя")
    
    first_name = input("Введите имя: ").strip()
    last_name = input("Введите фамилию: ").strip()
    email = input("Введите email: ").strip()
    phone = input("Введите телефон: ").strip()
    
    if not first_name or not last_name:
        print("Имя и фамилия обязательны для заполнения!")
        return
    
    cursor = connection.cursor()
    query = "INSERT INTO Readers (first_name, last_name, email, phone) VALUES (%s, %s, %s, %s)"
    values = (first_name, last_name, email if email else None, phone if phone else None)
    
    try:
        cursor.execute(query, values)
        connection.commit()
        print(f"Читатель {first_name} {last_name} успешно добавлен!")
        print(f"    Его ID: {cursor.lastrowid}")
    except Error as e:
        print(f"Ошибка при добавлении: {e}")
        if "Duplicate entry" in str(e):
            print("    Возможно, такой email уже существует")
    finally:
        cursor.close()

def loan_book(connection):
    print("\nВыдача книги")
    
    show_available_books(connection)
    
    try:
        reader_id = int(input("\nВведите ID читателя: "))
        book_id = int(input("Введите ID книги: "))
    except ValueError:
        print("ID должен быть числом!")
        return
    
    cursor = connection.cursor()
    
    try:
        cursor.execute("SELECT first_name, last_name FROM Readers WHERE reader_id = %s", (reader_id,))
        reader = cursor.fetchone()
        if not reader:
            print(f"Читатель с ID {reader_id} не найден!")
            return
        
        cursor.execute("SELECT title, available_copies FROM Books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            print(f"Книга с ID {book_id} не найдена!")
            return
        
        if book[1] <= 0:
            print(f"Книга '{book[0]}' недоступна для выдачи!")
            return
        
        loan_date = date.today()
        due_date = loan_date + timedelta(days=14)
        
        insert_loan = """
        INSERT INTO Loans (reader_id, book_id, loan_date, due_date) 
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_loan, (reader_id, book_id, loan_date, due_date))
        
        update_book = "UPDATE Books SET available_copies = available_copies - 1 WHERE book_id = %s"
        cursor.execute(update_book, (book_id,))
        
        connection.commit()
        print(f"\nКнига '{book[0]}' выдана читателю {reader[0]} {reader[1]}")
        print(f"    Дата возврата: {due_date.strftime('%d.%m.%Y')}")
        
    except Error as e:
        connection.rollback()
        print(f"Ошибка при выдаче книги: {e}")
    finally:
        cursor.close()

def return_book(connection):
    print("\nВозврат книги")
    
    try:
        loan_id = int(input("Введите ID записи о выдаче (loan_id): "))
    except ValueError:
        print("ID должен быть числом!")
        return
    
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            SELECT l.loan_id, b.title, r.first_name, r.last_name, l.return_date
            FROM Loans l
            JOIN Books b ON l.book_id = b.book_id
            JOIN Readers r ON l.reader_id = r.reader_id
            WHERE l.loan_id = %s
        """, (loan_id,))
        
        loan = cursor.fetchone()
        
        if not loan:
            print(f"Запись о выдаче с ID {loan_id} не найдена!")
            return
        
        if loan[4] is not None:
            print(f"Книга '{loan[1]}' уже была возвращена!")
            return
        
        update_loan = "UPDATE Loans SET return_date = CURDATE() WHERE loan_id = %s"
        cursor.execute(update_loan, (loan_id,))
        
        cursor.execute("""
            UPDATE Books 
            SET available_copies = available_copies + 1 
            WHERE book_id = (SELECT book_id FROM Loans WHERE loan_id = %s)
        """, (loan_id,))
        
        connection.commit()
        print(f"Книга '{loan[1]}' возвращена читателем {loan[2]} {loan[3]}")
        
    except Error as e:
        connection.rollback()
        print(f"Ошибка при возврате книги: {e}")
    finally:
        cursor.close()

def show_active_loans(connection):
    cursor = connection.cursor()
    
    query = """
    SELECT 
        l.loan_id,
        r.first_name,
        r.last_name,
        b.title,
        l.loan_date,
        l.due_date,
        DATEDIFF(CURDATE(), l.due_date) as overdue_days
    FROM Loans l
    JOIN Readers r ON l.reader_id = r.reader_id
    JOIN Books b ON l.book_id = b.book_id
    WHERE l.return_date IS NULL
    ORDER BY l.due_date
    """
    
    try:
        cursor.execute(query)
        loans = cursor.fetchall()
        
        if not loans:
            print("\nНет активных выдач.")
            return
        
        print("\n" + "=" * 100)
        print(f"{'ID':<4} | {'Читатель':<25} | {'Книга':<30} | {'Должен вернуть':<12} | {'Просрочка':<10}")
        print("-" * 100)
        
        for loan in loans:
            reader_name = f"{loan[1]} {loan[2]}"
            due_date = loan[5].strftime('%d.%m.%Y') if loan[5] else "—"
            overdue = f"{loan[6]} дн." if loan[6] and loan[6] > 0 else "Нет"
            
            print(f"{loan[0]:<4} | {reader_name:<25} | {loan[3]:<30} | {due_date:<12} | {overdue:<10}")
        
        print("=" * 100)
        
    except Error as e:
        print(f"Ошибка: {e}")
    finally:
        cursor.close()

def main():
    print("\n" + "=" * 50)
    print("   Система управления")
    print("=" * 50)
    
    connection = create_connection()
    if connection is None:
        input("\nНажми Enter для выхода...")
        return
    
    while True:
        print("\n" + "-" * 40)
        print("Главное меню")
        print("-" * 40)
        print("1. Показать все книги")
        print("2. Показать всех читателей")
        print("3. Добавить нового читателя")
        print("4. Выдать книгу")
        print("5. Вернуть книгу")
        print("6. Показать активные выдачи")
        print("0. Выход")
        print("-" * 40)
        
        choice = input("Выберите действие (0-6): ").strip()
        
        if choice == '1':
            show_all_books(connection)
        elif choice == '2':
            show_all_readers(connection)
        elif choice == '3':
            add_new_reader(connection)
        elif choice == '4':
            loan_book(connection)
        elif choice == '5':
            return_book(connection)
        elif choice == '6':
            show_active_loans(connection)
        elif choice == '0':
            print("\nРабота завершена. До свидания!")
            break
        else:
            print("Неверный выбор. Пожалуйста, выберите 0-6.")
    
    if connection.is_connected():
        connection.close()
        print("Соединение с базой данных закрыто.")

if __name__ == "__main__":
    main()