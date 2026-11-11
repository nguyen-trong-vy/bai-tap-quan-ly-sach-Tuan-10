from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --- CẤU HÌNH CƠ SỞ DỮ LIỆU SQLITE  ---
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-chi-dung-khi-phat-trien"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///qlsach.db"

db.init_app(app)


# --- KHAI BÁO MODEL (DANH MỤC SÁCH & SÁCH) ---
class Category(db.Model):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), default="")

    # Quan hệ 1 - Nhiều với bảng Book
    books: Mapped[list["Book"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.id} {self.name}>"


class Book(db.Model):
    __tablename__ = "book"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    title: Mapped[str] = mapped_column(String(150))
    author: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(default=0.0)
    quantity: Mapped[int] = mapped_column(default=1)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))

    # Quan hệ thuộc về một Category
    category: Mapped["Category"] = relationship(back_populates="books")

    def __repr__(self):
        return f"<Book {self.code} {self.title}>"


# Tự động tạo bảng nếu chưa tồn tại
with app.app_context():
    db.create_all()


# --- FILTER TUỲ BIẾN ĐỊNH DẠNG TIỀN VNĐ (C4) ---
@app.template_filter("vnd")
def format_vnd(value):
    try:
        val = int(round(float(value)))
        return f"{val:,}".replace(",", ".") + " đ"
    except (ValueError, TypeError):
        return "0 đ"


# --- HÀM KIỂM TRA DỮ LIỆU NHẬP FORM (C5) ---
def parse_positive_float(val_str, field_label="Giá sách"):
    if val_str is None or val_str.strip() == "":
        return None, f"Vui lòng nhập {field_label.lower()}."
    cleaned = val_str.strip().replace(",", ".")
    try:
        val = float(cleaned)
    except ValueError:
        return None, f"{field_label} phải là một số hợp lệ."
    if val < 0:
        return None, f"{field_label} không được nhỏ hơn 0."
    return val, None


def parse_positive_int(val_str, field_label="Số lượng"):
    if val_str is None or val_str.strip() == "":
        return None, f"Vui lòng nhập {field_label.lower()}."
    try:
        val = int(val_str.strip())
    except ValueError:
        return None, f"{field_label} phải là một số nguyên."
    if val < 0:
        return None, f"{field_label} không được nhỏ hơn 0."
    return val, None


# =========================================================
# 3. DASHBOARD QUẢN LÝ DANH MỤC SÁCH VÀ SÁCH
# =========================================================
@app.get("/")
def dashboard():
    total_categories = db.session.scalar(db.select(func.count(Category.id))) or 0
    total_books = db.session.scalar(db.select(func.count(Book.id))) or 0
    total_quantity = db.session.scalar(db.select(func.sum(Book.quantity))) or 0
    avg_price = db.session.scalar(db.select(func.avg(Book.price))) or 0.0

    # Lấy toàn bộ danh mục kèm danh sách sách
    categories = db.session.execute(
        db.select(Category).order_by(Category.name)
    ).scalars().all()

    # Lấy 5 cuốn sách mới thêm gần nhất
    recent_books = db.session.execute(
        db.select(Book).order_by(Book.id.desc()).limit(5)
    ).scalars().all()

    return render_template(
        "dashboard.html",
        total_categories=total_categories,
        total_books=total_books,
        total_quantity=total_quantity,
        avg_price=avg_price,
        categories=categories,
        recent_books=recent_books,
    )


# --- ROUTE THÊM DỮ LIỆU MẪU (SEEDING DATA - CHƯƠNG 6) ---
@app.get("/them-mau")
def seed_data():
    total = db.session.scalar(db.select(func.count(Category.id)))
    if total > 0:
        flash(f"CSDL đã có {total} danh mục, không thêm dữ liệu mẫu nữa.", "warning")
        return redirect(url_for("dashboard"))

    cat_cntt = Category(name="Công nghệ thông tin", description="Sách lập trình, phần mềm mã nguồn mở, mạng máy tính và CSDL")
    cat_vh = Category(name="Văn học", description="Tiểu thuyết, truyện ngắn, tác phẩm văn học trong và ngoài nước")
    cat_kt = Category(name="Kinh tế - Kỹ năng", description="Sách quản trị kinh doanh, tài chính và phát triển bản thân")
    cat_kh = Category(name="Khoa học - Tự nhiên", description="Sách toán học, vật lý, vũ trụ và khoa học ứng dụng")

    db.session.add_all([cat_cntt, cat_vh, cat_kt, cat_kh])
    db.session.flush()  # Lấy ID của các danh mục vừa tạo

    sample_books = [
        Book(code="SACH001", title="Lập trình Web với Flask và Python", author="Nguyễn Dũng", price=125000, quantity=15, category_id=cat_cntt.id),
        Book(code="SACH002", title="Cơ sở dữ liệu SQLAlchemy thực chiến", author="Trần Văn An", price=140000, quantity=10, category_id=cat_cntt.id),
        Book(code="SACH003", title="Nhập môn Phần mềm Mã nguồn mở", author="Lê Hoàng Cường", price=95000, quantity=20, category_id=cat_cntt.id),
        Book(code="SACH004", title="Mắt Biếc", author="Nguyễn Nhật Ánh", price=85000, quantity=12, category_id=cat_vh.id),
        Book(code="SACH005", title="Dế Mèn Phiêu Lưu Ký", author="Tô Hoài", price=60000, quantity=8, category_id=cat_vh.id),
        Book(code="SACH006", title="Đắc Nhân Tâm", author="Dale Carnegie", price=90000, quantity=25, category_id=cat_kt.id),
        Book(code="SACH007", title="Tư Duy Nhanh Và Chậm", author="Daniel Kahneman", price=185000, quantity=7, category_id=cat_kt.id),
        Book(code="SACH008", title="Lược Sử Thời Gian", author="Stephen Hawking", price=115000, quantity=5, category_id=cat_kh.id),
    ]
    db.session.add_all(sample_books)
    db.session.commit()

    flash("Đã khởi tạo 4 danh mục và 8 cuốn sách mẫu thành công!", "success")
    return redirect(url_for("dashboard"))


# =========================================================
# 1. CRUD DANH MỤC SÁCH
# =========================================================
@app.get("/categories")
def category_list():
    q = request.args.get("q", "").strip()
    stmt = db.select(Category).order_by(Category.id)
    if q:
        stmt = stmt.where(Category.name.ilike(f"%{q}%"))
    categories = db.session.execute(stmt).scalars().all()
    return render_template("categories.html", categories=categories, q=q)


@app.route("/categories/add", methods=["GET", "POST"])
def category_add():
    errors = {}
    name_raw = ""
    desc_raw = ""

    if request.method == "POST":
        name_raw = request.form.get("name", "").strip()
        desc_raw = request.form.get("description", "").strip()

        if not name_raw:
            errors["name"] = "Vui lòng nhập tên danh mục."
        else:
            existing = db.session.scalar(
                db.select(Category).where(func.lower(Category.name) == name_raw.lower())
            )
            if existing:
                errors["name"] = "Tên danh mục này đã tồn tại."

        if not errors:
            new_cat = Category(name=name_raw, description=desc_raw)
            db.session.add(new_cat)
            db.session.commit()
            flash(f"Đã thêm danh mục '{new_cat.name}' thành công!", "success")
            return redirect(url_for("category_list"))

    return render_template(
        "category_form.html",
        mode="add",
        name=name_raw,
        description=desc_raw,
        errors=errors,
    )


@app.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
def category_edit(cat_id):
    category = db.session.get(Category, cat_id)
    if not category:
        abort(404, description=f"Không tìm thấy danh mục có ID = {cat_id}.")

    errors = {}
    name_raw = category.name
    desc_raw = category.description or ""

    if request.method == "POST":
        name_raw = request.form.get("name", "").strip()
        desc_raw = request.form.get("description", "").strip()

        if not name_raw:
            errors["name"] = "Vui lòng nhập tên danh mục."
        else:
            existing = db.session.scalar(
                db.select(Category).where(
                    func.lower(Category.name) == name_raw.lower(),
                    Category.id != cat_id,
                )
            )
            if existing:
                errors["name"] = "Tên danh mục này đã tồn tại."

        if not errors:
            category.name = name_raw
            category.description = desc_raw
            db.session.commit()
            flash(f"Đã cập nhật danh mục '{category.name}'!", "success")
            return redirect(url_for("category_list"))

    return render_template(
        "category_form.html",
        mode="edit",
        category=category,
        name=name_raw,
        description=desc_raw,
        errors=errors,
    )


@app.post("/categories/<int:cat_id>/delete")
def category_delete(cat_id):
    category = db.session.get(Category, cat_id)
    if not category:
        abort(404, description=f"Không tìm thấy danh mục có ID = {cat_id}.")

    cat_name = category.name
    book_count = len(category.books)
    db.session.delete(category)
    db.session.commit()
    flash(f"Đã xoá danh mục '{cat_name}' (cùng {book_count} sách thuộc danh mục).", "info")
    return redirect(url_for("category_list"))


# =========================================================
# 2. CRUD SÁCH THEO DANH MỤC
# =========================================================
@app.get("/books")
def book_list():
    q = request.args.get("q", "").strip()
    cat_id_raw = request.args.get("category_id", "").strip()
    selected_cat_id = None

    stmt = db.select(Book).order_by(Book.id.desc())

    if cat_id_raw:
        try:
            selected_cat_id = int(cat_id_raw)
            stmt = stmt.where(Book.category_id == selected_cat_id)
        except ValueError:
            selected_cat_id = None

    if q:
        stmt = stmt.where(
            (Book.title.ilike(f"%{q}%"))
            | (Book.code.ilike(f"%{q}%"))
            | (Book.author.ilike(f"%{q}%"))
        )

    books = db.session.execute(stmt).scalars().all()
    categories = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        selected_cat_id=selected_cat_id,
        q=q,
    )


@app.route("/books/add", methods=["GET", "POST"])
def book_add():
    categories = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    if not categories:
        flash("Vui lòng tạo ít nhất 1 Danh mục Sách trước khi thêm sách!", "warning")
        return redirect(url_for("category_add"))

    errors = {}
    code_raw = ""
    title_raw = ""
    author_raw = ""
    price_raw = ""
    quantity_raw = "1"
    category_id_raw = request.args.get("category_id", str(categories[0].id))

    if request.method == "POST":
        code_raw = request.form.get("code", "").strip().upper()
        title_raw = request.form.get("title", "").strip()
        author_raw = request.form.get("author", "").strip()
        price_raw = request.form.get("price", "")
        quantity_raw = request.form.get("quantity", "")
        category_id_raw = request.form.get("category_id", "")

        # 1. Kiểm tra mã sách
        if not code_raw:
            errors["code"] = "Vui lòng nhập mã sách."
        else:
            existing_book = db.session.scalar(
                db.select(Book).where(func.upper(Book.code) == code_raw)
            )
            if existing_book:
                errors["code"] = "Mã sách này đã tồn tại."

        # 2. Kiểm tra tên sách
        if not title_raw:
            errors["title"] = "Vui lòng nhập tên sách."

        # 3. Kiểm tra tác giả
        if not author_raw:
            errors["author"] = "Vui lòng nhập tên tác giả."

        # 4. Kiểm tra giá sách 
        price_val, err_price = parse_positive_float(price_raw, "Giá sách")
        if err_price:
            errors["price"] = err_price

        # 5. Kiểm tra số lượng
        qty_val, err_qty = parse_positive_int(quantity_raw, "Số lượng")
        if err_qty:
            errors["quantity"] = err_qty

        # 6. Kiểm tra danh mục
        cat_obj = None
        try:
            cat_obj = db.session.get(Category, int(category_id_raw))
        except (ValueError, TypeError):
            cat_obj = None
        if not cat_obj:
            errors["category_id"] = "Danh mục đã chọn không hợp lệ."

        if not errors:
            new_book = Book(
                code=code_raw,
                title=title_raw,
                author=author_raw,
                price=price_val,
                quantity=qty_val,
                category_id=cat_obj.id,
            )
            db.session.add(new_book)
            db.session.commit()
            flash(f"Đã thêm sách '{new_book.title}' vào danh mục '{cat_obj.name}'!", "success")
            return redirect(url_for("book_list", category_id=cat_obj.id))

    return render_template(
        "book_form.html",
        mode="add",
        categories=categories,
        code=code_raw,
        title=title_raw,
        author=author_raw,
        price=price_raw,
        quantity=quantity_raw,
        category_id=str(category_id_raw),
        errors=errors,
    )


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def book_edit(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404, description=f"Không tìm thấy sách có ID = {book_id}.")

    categories = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    errors = {}

    code_raw = book.code
    title_raw = book.title
    author_raw = book.author
    price_raw = str(int(book.price) if book.price == int(book.price) else book.price)
    quantity_raw = str(book.quantity)
    category_id_raw = str(book.category_id)

    if request.method == "POST":
        code_raw = request.form.get("code", "").strip().upper()
        title_raw = request.form.get("title", "").strip()
        author_raw = request.form.get("author", "").strip()
        price_raw = request.form.get("price", "")
        quantity_raw = request.form.get("quantity", "")
        category_id_raw = request.form.get("category_id", "")

        if not code_raw:
            errors["code"] = "Vui lòng nhập mã sách."
        else:
            existing_book = db.session.scalar(
                db.select(Book).where(
                    func.upper(Book.code) == code_raw,
                    Book.id != book_id,
                )
            )
            if existing_book:
                errors["code"] = "Mã sách này đã được dùng cho sách khác."

        if not title_raw:
            errors["title"] = "Vui lòng nhập tên sách."

        if not author_raw:
            errors["author"] = "Vui lòng nhập tên tác giả."

        price_val, err_price = parse_positive_float(price_raw, "Giá sách")
        if err_price:
            errors["price"] = err_price

        qty_val, err_qty = parse_positive_int(quantity_raw, "Số lượng")
        if err_qty:
            errors["quantity"] = err_qty

        cat_obj = None
        try:
            cat_obj = db.session.get(Category, int(category_id_raw))
        except (ValueError, TypeError):
            cat_obj = None
        if not cat_obj:
            errors["category_id"] = "Danh mục đã chọn không hợp lệ."

        if not errors:
            book.code = code_raw
            book.title = title_raw
            book.author = author_raw
            book.price = price_val
            book.quantity = qty_val
            book.category_id = cat_obj.id
            db.session.commit()
            flash(f"Đã cập nhật thông tin sách '{book.title}'!", "success")
            return redirect(url_for("book_list", category_id=cat_obj.id))

    return render_template(
        "book_form.html",
        mode="edit",
        book=book,
        categories=categories,
        code=code_raw,
        title=title_raw,
        author=author_raw,
        price=price_raw,
        quantity=quantity_raw,
        category_id=str(category_id_raw),
        errors=errors,
    )


@app.post("/books/<int:book_id>/delete")
def book_delete(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404, description=f"Không tìm thấy sách có ID = {book_id}.")

    title = book.title
    cat_id = book.category_id
    db.session.delete(book)
    db.session.commit()
    flash(f"Đã xoá sách '{title}' thành công.", "info")
    return redirect(url_for("book_list", category_id=cat_id))


# --- XỬ LÝ LỖI 404 (C3 & 4) ---
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", error=error), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
