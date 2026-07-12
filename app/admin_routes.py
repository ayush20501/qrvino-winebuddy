from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from app.config import create_database_connection
from functools import wraps
from werkzeug.utils import secure_filename
import os
import re
import csv
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

MYSQL_TYPES = [
    ('String',   ['VARCHAR', 'CHAR', 'TINYTEXT', 'TEXT', 'MEDIUMTEXT', 'LONGTEXT']),
    ('Numeric',  ['TINYINT', 'SMALLINT', 'INT', 'BIGINT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'BOOLEAN']),
    ('Date/Time',['DATE', 'DATETIME', 'TIMESTAMP', 'TIME', 'YEAR']),
    ('Binary',   ['BLOB', 'MEDIUMBLOB', 'LONGBLOB']),
    ('Other',    ['JSON']),
]

def build_col_type(type_name, length=None, precision=None, scale=None):
    t = type_name.upper().strip()
    if t in ('VARCHAR', 'CHAR'):
        l = int(length) if length and str(length).isdigit() and int(length) > 0 else 255
        return f'{t}({l})'
    if t == 'DECIMAL':
        p = int(precision) if precision and str(precision).isdigit() else 10
        s = int(scale) if scale and str(scale).isdigit() else 2
        return f'DECIMAL({p},{s})'
    return t

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated

def dump_database():
    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cursor.fetchall()]
        sql_lines = []
        for table in tables:
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_result = cursor.fetchone()
            create_sql = list(create_result.values())[1]
            sql_lines.append(f"DROP TABLE IF EXISTS `{table}`;")
            sql_lines.append(create_sql + ";\n")
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    cols = []
                    vals = []
                    for k, v in row.items():
                        cols.append(f"`{k}`")
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            escaped_v = str(v).replace("'", "''").replace("\\", "\\\\")
                            vals.append(f"'{escaped_v}'")
                    cols_str = ", ".join(cols)
                    vals_str = ", ".join(vals)
                    sql_lines.append(f"INSERT INTO `{table}` ({cols_str}) VALUES ({vals_str});")
                sql_lines.append("\n")
        return "\n".join(sql_lines)
    finally:
        cursor.close()
        conn.close()

def safe_name(name):
    return bool(name) and bool(re.match(r'^[A-Za-z0-9_]+$', str(name)))

def get_columns(cursor, table_name):
    cursor.execute(f'DESCRIBE `{table_name}`')
    return cursor.fetchall()

def get_pk(columns):
    return next((c['Field'] for c in columns if c['Key'] == 'PRI'), None)

def input_type_for(col):
    t = col['Type'].lower()
    if 'int' in t:
        return 'number'
    if 'text' in t or 'blob' in t:
        return 'textarea'
    if 'date' in t:
        return 'date'
    return 'text'

@admin_bp.route('/')
def index():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == os.getenv('ADMIN_PASSWORD', ''):
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        error = 'Invalid password'
    return render_template('admin/login.html', error=error)

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SHOW TABLES')
    raw = cursor.fetchall()
    tables = []
    for row in raw:
        name = list(row.values())[0]
        cursor.execute(f'SELECT COUNT(*) as cnt FROM `{name}`')
        tables.append({'name': name, 'count': cursor.fetchone()['cnt']})
    cursor.close()
    conn.close()
    return render_template('admin/dashboard.html', tables=tables, mysql_types=MYSQL_TYPES)

@admin_bp.route('/backup')
@login_required
def backup_database():
    try:
        sql_content = dump_database()
        response = Response(sql_content, mimetype='text/sql')
        response.headers['Content-Disposition'] = 'attachment; filename=db_backup.sql'
        return response
    except Exception as e:
        flash(f"Backup failed: {str(e)}", 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/table/create', methods=['POST'])
@login_required
def create_table():
    table_name = request.form.get('table_name', '').strip()
    if not safe_name(table_name):
        flash('Invalid table name. Use only letters, numbers and underscores.', 'error')
        return redirect(url_for('admin.dashboard'))

    col_names = request.form.getlist('col_name[]')
    col_types = request.form.getlist('col_type[]')
    col_lengths = request.form.getlist('col_length[]')
    col_precisions = request.form.getlist('col_precision[]')
    col_scales = request.form.getlist('col_scale[]')
    col_requireds = request.form.getlist('col_required[]')

    columns = ['`id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY']
    for i, name in enumerate(col_names):
        name = name.strip()
        if not name or not safe_name(name):
            continue
        sql_type = build_col_type(
            col_types[i] if i < len(col_types) else 'VARCHAR',
            col_lengths[i] if i < len(col_lengths) else None,
            col_precisions[i] if i < len(col_precisions) else None,
            col_scales[i] if i < len(col_scales) else None,
        )
        nullable = 'NOT NULL' if str(i) in col_requireds else 'DEFAULT NULL'
        columns.append(f'`{name}` {sql_type} {nullable}')

    conn = create_database_connection()
    cursor = conn.cursor()
    try:
        sql = f'CREATE TABLE `{table_name}` ({", ".join(columns)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci'
        cursor.execute(sql)
        conn.commit()
        flash(f'Table "{table_name}" created successfully.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/table/<table_name>/drop', methods=['POST'])
@login_required
def drop_table(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))
    conn = create_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'DROP TABLE `{table_name}`')
        conn.commit()
        flash(f'Table "{table_name}" deleted.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.dashboard'))

def parse_mysql_type(type_str):
    type_str = type_str.upper()
    if '(' in type_str:
        base_type, parts = type_str.split('(', 1)
        parts = parts.rstrip(')').split(',')
        if len(parts) == 2:
            return base_type, None, parts[0], parts[1]
        return base_type, parts[0], None, None
    return type_str, None, None, None

@admin_bp.route('/table/<table_name>')
@login_required
def table_detail(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))

    page = max(1, int(request.args.get('page', 1)))
    per_page = 20
    offset = (page - 1) * per_page

    sort_col = request.args.get('sort', '').strip()
    sort_order = request.args.get('order', 'asc').strip().upper()
    if sort_order not in ('ASC', 'DESC'):
        sort_order = 'ASC'

    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    columns = get_columns(cursor, table_name)
    pk_col = get_pk(columns)

    valid_cols = {c['Field'] for c in columns}
    if sort_col not in valid_cols:
        sort_col = ''

    cursor.execute(f'SELECT COUNT(*) as cnt FROM `{table_name}`')
    total = cursor.fetchone()['cnt']
    total_pages = max(1, (total + per_page - 1) // per_page)

    if sort_col:
        query = f'SELECT * FROM `{table_name}` ORDER BY `{sort_col}` {sort_order} LIMIT %s OFFSET %s'
    else:
        query = f'SELECT * FROM `{table_name}` LIMIT %s OFFSET %s'

    cursor.execute(query, (per_page, offset))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    parsed_columns = []
    for col in columns:
        col_type, length, precision, scale = parse_mysql_type(col['Type'])
        col['ParsedType'] = col_type
        col['ParsedLength'] = length or ''
        col['ParsedPrecision'] = precision or ''
        col['ParsedScale'] = scale or ''
        parsed_columns.append(col)

    return render_template('admin/table_detail.html',
        table_name=table_name,
        columns=parsed_columns,
        rows=rows,
        pk_col=pk_col,
        page=page,
        total_pages=total_pages,
        total=total,
        sort_col=sort_col,
        sort_order=sort_order.lower(),
        mysql_types=MYSQL_TYPES
    )

@admin_bp.route('/table/<table_name>/add-column', methods=['POST'])
@login_required
def add_column(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))

    col_name = request.form.get('col_name', '').strip()
    col_type = request.form.get('col_type', 'VARCHAR')
    required = request.form.get('required') == 'on'

    if not safe_name(col_name):
        flash('Invalid column name. Use only letters, numbers and underscores.', 'error')
        return redirect(url_for('admin.table_detail', table_name=table_name))

    sql_type = build_col_type(
        col_type,
        request.form.get('col_length'),
        request.form.get('col_precision'),
        request.form.get('col_scale'),
    )
    nullable = 'NOT NULL DEFAULT \'\'' if required else 'DEFAULT NULL'

    conn = create_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {sql_type} {nullable}')
        conn.commit()
        flash(f'Column "{col_name}" added.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.table_detail', table_name=table_name))

@admin_bp.route('/table/<table_name>/add-row', methods=['GET', 'POST'])
@login_required
def add_row(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))

    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    columns = get_columns(cursor, table_name)
    editable = [c for c in columns if c['Extra'] != 'auto_increment']

    if request.method == 'POST':
        col_names = [c['Field'] for c in editable]
        values = []
        for c in col_names:
            if c == 'LOGO_PATH':
                file = request.files.get('LOGO_PATH_file')
                if file and file.filename:
                    filename = f'logo_new_{os.urandom(4).hex()}.png'
                    logos_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'logos')
                    os.makedirs(logos_dir, exist_ok=True)
                    file.save(os.path.join(logos_dir, filename))
                    values.append(f'logos/{filename}')
                else:
                    values.append(request.form.get(c) or None)
            else:
                values.append(request.form.get(c) or None)
        col_list = ','.join(f'`{c}`' for c in col_names)
        placeholders = ','.join(['%s'] * len(col_names))
        try:
            cursor.execute(f'INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})', values)
            conn.commit()
            flash('Row added successfully.', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.table_detail', table_name=table_name))
        except Exception as e:
            flash(str(e), 'error')

    cursor.close()
    conn.close()
    return render_template('admin/row_form.html',
        table_name=table_name,
        columns=editable,
        row=None,
        action='Add',
        input_type_for=input_type_for
    )

@admin_bp.route('/table/<table_name>/edit/<pk_val>', methods=['GET', 'POST'])
@login_required
def edit_row(table_name, pk_val):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))

    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    columns = get_columns(cursor, table_name)
    pk_col = get_pk(columns)
    editable = [c for c in columns if c['Extra'] != 'auto_increment']

    if request.method == 'POST':
        col_names = [c['Field'] for c in editable]
        values = []
        for c in col_names:
            if c == 'LOGO_PATH':
                file = request.files.get('LOGO_PATH_file')
                if file and file.filename:
                    filename = f'logo_{pk_val}.png'
                    logos_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'logos')
                    os.makedirs(logos_dir, exist_ok=True)
                    file.save(os.path.join(logos_dir, filename))
                    values.append(f'logos/{filename}')
                else:
                    values.append(request.form.get(c) or None)
            else:
                values.append(request.form.get(c) or None)
        set_clause = ','.join(f'`{c}`=%s' for c in col_names)
        values.append(pk_val)
        try:
            cursor.execute(f'UPDATE `{table_name}` SET {set_clause} WHERE `{pk_col}`=%s', values)
            conn.commit()
            flash('Row updated successfully.', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.table_detail', table_name=table_name))
        except Exception as e:
            flash(str(e), 'error')

    cursor.execute(f'SELECT * FROM `{table_name}` WHERE `{pk_col}`=%s', (pk_val,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('admin/row_form.html',
        table_name=table_name,
        columns=editable,
        row=row,
        action='Edit',
        input_type_for=input_type_for
    )

@admin_bp.route('/table/<table_name>/delete/<pk_val>', methods=['POST'])
@login_required
def delete_row(table_name, pk_val):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))

    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    columns = get_columns(cursor, table_name)
    pk_col = get_pk(columns)
    try:
        cursor.execute(f'DELETE FROM `{table_name}` WHERE `{pk_col}`=%s', (pk_val,))
        conn.commit()
        flash('Row deleted.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.table_detail', table_name=table_name))

@admin_bp.route('/table/<table_name>/export')
@login_required
def export_table(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))
    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        columns = [c['Field'] for c in get_columns(cursor, table_name)]
        cursor.execute(f'SELECT * FROM `{table_name}`')
        rows = cursor.fetchall()
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(columns)
        for row in rows:
            cw.writerow([row[col] for col in columns])
        response = Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename={table_name}.csv'
        return response
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('admin.table_detail', table_name=table_name))
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/table/<table_name>/import', methods=['POST'])
@login_required
def import_table(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'error')
        return redirect(url_for('admin.table_detail', table_name=table_name))
    conn = create_database_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        db_cols = {c['Field'] for c in get_columns(cursor, table_name)}
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'), newline=None)
        csv_reader = csv.reader(stream)
        headers = next(csv_reader, None)
        if not headers:
            flash('The uploaded CSV file is empty.', 'error')
            return redirect(url_for('admin.table_detail', table_name=table_name))
        valid_indices = []
        valid_cols = []
        for idx, h in enumerate(headers):
            if h in db_cols:
                valid_indices.append(idx)
                valid_cols.append(h)
        if not valid_cols:
            flash('No matching columns found between CSV and database table.', 'error')
            return redirect(url_for('admin.table_detail', table_name=table_name))
        col_list = ', '.join(f'`{c}`' for c in valid_cols)
        placeholders = ', '.join(['%s'] * len(valid_cols))
        update_clause = ', '.join(f'`{c}`=VALUES(`{c}`)' for c in valid_cols)
        sql = f'INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}'
        rows_inserted_or_updated = 0
        for row in csv_reader:
            if not row:
                continue
            row_vals = []
            for idx in valid_indices:
                val = row[idx] if idx < len(row) else ''
                if val == '':
                    row_vals.append(None)
                else:
                    row_vals.append(val)
            cursor.execute(sql, row_vals)
            rows_inserted_or_updated += 1
        conn.commit()
        flash(f'Successfully imported {rows_inserted_or_updated} rows.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Import failed: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.table_detail', table_name=table_name))

@admin_bp.route('/table/<table_name>/change-column', methods=['POST'])
@login_required
def change_column(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    col_type = request.form.get('col_type', 'VARCHAR').strip()
    required = request.form.get('required') == 'on'
    default_val = request.form.get('default_val', '')
    if not safe_name(old_name) or not safe_name(new_name):
        flash('Invalid column name.', 'error')
        return redirect(url_for('admin.table_detail', table_name=table_name))
    sql_type = build_col_type(
        col_type,
        request.form.get('col_length'),
        request.form.get('col_precision'),
        request.form.get('col_scale'),
    )
    nullable = 'NOT NULL' if required else 'NULL'
    if default_val == '':
        default_clause = 'DEFAULT NULL' if not required else ''
    else:
        default_clause = f"DEFAULT '{default_val}'"
    conn = create_database_connection()
    cursor = conn.cursor()
    try:
        sql = f'ALTER TABLE `{table_name}` CHANGE COLUMN `{old_name}` `{new_name}` {sql_type} {nullable} {default_clause}'
        cursor.execute(sql)
        conn.commit()
        flash(f'Column "{old_name}" updated successfully.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.table_detail', table_name=table_name) + '?active_tab=structure')

@admin_bp.route('/table/<table_name>/drop-column', methods=['POST'])
@login_required
def drop_column(table_name):
    if not safe_name(table_name):
        flash('Invalid table name.', 'error')
        return redirect(url_for('admin.dashboard'))
    col_name = request.form.get('col_name', '').strip()
    if not safe_name(col_name):
        flash('Invalid column name.', 'error')
        return redirect(url_for('admin.table_detail', table_name=table_name))
    conn = create_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'ALTER TABLE `{table_name}` DROP COLUMN `{col_name}`')
        conn.commit()
        flash(f'Column "{col_name}" dropped successfully.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin.table_detail', table_name=table_name) + '?active_tab=structure')

