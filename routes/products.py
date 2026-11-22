from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.db import get_db

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/', methods=['GET'])
def list_products():
    search = request.args.get('search', '').strip()
    filter_low_stock = request.args.get('low_stock', '').strip() == '1'
    
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if search:
            query += " AND (product_name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if filter_low_stock:
            query += " AND stock <= minimum_stock"

        query += " ORDER BY product_id DESC"
        products = cursor.execute(query, params).fetchall()

        # Count low stock products for badge
        cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= minimum_stock")
        low_stock_count = cursor.fetchone()[0]

        return render_template(
            'products.html',
            products=products,
            search=search,
            filter_low_stock=filter_low_stock,
            low_stock_count=low_stock_count
        )
    finally:
        conn.close()

@products_bp.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('product_name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '').strip()
        gst_str = request.form.get('gst_rate', '18').strip()
        stock_str = request.form.get('stock', '0').strip()
        min_stock_str = request.form.get('minimum_stock', '5').strip()

        if not name:
            flash("Product name is required.", "danger")
            return render_template('product_form.html', action='Add', product=request.form)

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError()
        except ValueError:
            flash("Unit price must be a valid non-negative number.", "danger")
            return render_template('product_form.html', action='Add', product=request.form)

        try:
            gst_rate = float(gst_str)
            if gst_rate < 0 or gst_rate > 100:
                raise ValueError()
        except ValueError:
            flash("GST rate must be a valid percentage between 0 and 100.", "danger")
            return render_template('product_form.html', action='Add', product=request.form)

        try:
            stock = int(stock_str)
            if stock < 0:
                raise ValueError()
        except ValueError:
            flash("Stock quantity must be a non-negative integer.", "danger")
            return render_template('product_form.html', action='Add', product=request.form)

        try:
            min_stock = int(min_stock_str)
            if min_stock < 0:
                raise ValueError()
        except ValueError:
            flash("Minimum stock threshold must be a non-negative integer.", "danger")
            return render_template('product_form.html', action='Add', product=request.form)

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (product_name, description, price, gst_rate, stock, minimum_stock)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, description, price, gst_rate, stock, min_stock))
            conn.commit()
            flash(f"Product '{name}' added successfully.", "success")
            return redirect(url_for('products.list_products'))
        except Exception as e:
            flash(f"Error saving product: {str(e)}", "danger")
            return render_template('product_form.html', action='Add', product=request.form)
        finally:
            conn.close()

    return render_template('product_form.html', action='Add', product={'gst_rate': 18.0, 'stock': 0, 'minimum_stock': 5})

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            flash("Product not found.", "warning")
            return redirect(url_for('products.list_products'))

        if request.method == 'POST':
            name = request.form.get('product_name', '').strip()
            description = request.form.get('description', '').strip()
            price_str = request.form.get('price', '').strip()
            gst_str = request.form.get('gst_rate', '18').strip()
            stock_str = request.form.get('stock', '0').strip()
            min_stock_str = request.form.get('minimum_stock', '5').strip()

            if not name:
                flash("Product name is required.", "danger")
                return render_template('product_form.html', action='Edit', product=request.form)

            try:
                price = float(price_str)
                if price < 0:
                    raise ValueError()
            except ValueError:
                flash("Unit price must be a valid non-negative number.", "danger")
                return render_template('product_form.html', action='Edit', product=request.form)

            try:
                gst_rate = float(gst_str)
                if gst_rate < 0 or gst_rate > 100:
                    raise ValueError()
            except ValueError:
                flash("GST rate must be a valid percentage.", "danger")
                return render_template('product_form.html', action='Edit', product=request.form)

            try:
                stock = int(stock_str)
                if stock < 0:
                    raise ValueError()
            except ValueError:
                flash("Stock must be a non-negative integer.", "danger")
                return render_template('product_form.html', action='Edit', product=request.form)

            try:
                min_stock = int(min_stock_str)
                if min_stock < 0:
                    raise ValueError()
            except ValueError:
                flash("Minimum stock must be a non-negative integer.", "danger")
                return render_template('product_form.html', action='Edit', product=request.form)

            cursor.execute("""
                UPDATE products
                SET product_name = ?, description = ?, price = ?, gst_rate = ?, stock = ?, minimum_stock = ?
                WHERE product_id = ?
            """, (name, description, price, gst_rate, stock, min_stock, product_id))
            conn.commit()
            flash(f"Product '{name}' updated successfully.", "success")
            return redirect(url_for('products.list_products'))

        return render_template('product_form.html', action='Edit', product=dict(product))
    finally:
        conn.close()

@products_bp.route('/update-stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    adjustment_str = request.form.get('adjustment', '0').strip()
    try:
        adjustment = int(adjustment_str)
    except ValueError:
        flash("Invalid quantity entered.", "danger")
        return redirect(url_for('products.list_products'))

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT stock, product_name FROM products WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            flash("Product not found.", "danger")
            return redirect(url_for('products.list_products'))

        new_stock = row['stock'] + adjustment
        if new_stock < 0:
            flash(f"Cannot reduce stock below zero. Current stock is {row['stock']}.", "danger")
            return redirect(url_for('products.list_products'))

        cursor.execute("UPDATE products SET stock = ? WHERE product_id = ?", (new_stock, product_id))
        conn.commit()
        flash(f"Stock for '{row['product_name']}' updated to {new_stock}.", "success")
    finally:
        conn.close()

    return redirect(url_for('products.list_products'))

@products_bp.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Verify if product is in invoice_items
        cursor.execute("SELECT COUNT(*) FROM invoice_items WHERE product_id = ?", (product_id,))
        used_count = cursor.fetchone()[0]
        if used_count > 0:
            flash(f"Cannot delete product. It is referenced in {used_count} historical invoice line items.", "danger")
            return redirect(url_for('products.list_products'))

        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()
        flash("Product deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting product: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('products.list_products'))

@products_bp.route('/api/list', methods=['GET'])
def api_list_products():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_id, product_name, price, gst_rate, stock, minimum_stock
            FROM products
            ORDER BY product_name ASC
        """)
        products = [dict(row) for row in cursor.fetchall()]
        return jsonify({'products': products})
    finally:
        conn.close()

