from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
from .auth import login_required
from .models import (
    get_all_meetings_with_items,
    create_meeting_and_agendas,
    delete_meeting_from_db,
    delete_agenda_item_from_db,
    get_agenda_item_by_id,
    get_next_agenda_item_number # Import this
)
from .utils import allowed_file
# ...existing code...
from .models import get_agenda_items_for_meeting
# ...existing code...

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required()
def home_redirect():
    return redirect(url_for('main.index'))

@main_bp.route('/index')
@login_required()
def index():
    user_role = session.get('user_role')
    search_query = request.args.get('search', '')
    start_date_query = request.args.get('start_date', '')
    end_date_query = request.args.get('end_date', '')

    try:
        meetings = get_all_meetings_with_items(
            search_term=search_query, 
            start_date=start_date_query, 
            end_date=end_date_query
        )
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการดึงข้อมูลการประชุม: {e}", "danger")
        meetings = []

    return render_template('index.html',
                           title="วาระการประชุม",
                           meetings=meetings,
                           user_role=user_role,
                           search_query=search_query,
                           start_date_query=start_date_query,
                           end_date_query=end_date_query)

@main_bp.route('/upload_agenda', methods=['POST'])
@login_required(role='admin')
def upload_agenda():
    if request.method == 'POST':
        title = request.form.get('meeting_title')
        instance = request.form.get('meeting_instance')
        meeting_date = request.form.get('meeting_date')
        username = session.get('username', 'UnknownAdmin')

        if not title or not meeting_date:
            flash("กรุณากรอกชื่อเรื่องการประชุมและวันที่มีการประชุม", "warning")
            return redirect(url_for('main.index'))

        agenda_files_info = []
        upload_folder_path = os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_folder_path, exist_ok=True)


        # --- Handling dynamic agenda items ---
        # The form sends agenda_item_title_X and agenda_item_file_X
        # We need to find the highest X to iterate correctly.
        # A better way is to use request.form.getlist('agenda_item_title[]') if names are like agenda_item_title[]
        # For now, let's assume JavaScript correctly numbers them and we can find them.

        idx = 1
        next_item_number_in_db = 1 # For a new meeting, this will be the case.
                                   # If editing existing, this needs to be calculated based on existing items.
                                   # The simplified request implies adding new meetings mostly.

        # This part needs to robustly collect files and their corresponding item numbers from the form
        # The current JS logic will send agenda_item_file_1, agenda_item_file_2 etc.
        # And the JS will also manage the "วาระที่ X" label dynamically.

        temp_agenda_items = [] # To hold items collected from form

        # Collect all uploaded files first
        files = request.files
        processed_indices = set()

        # Loop through form keys to find agenda files
        for key in request.form.keys():
            if key.startswith('agenda_item_number_'):
                current_idx_str = key.split('_')[-1]
                try:
                    current_idx_form = int(current_idx_str) # This is the display number from the form
                    file_key = f'agenda_item_file_{current_idx_form}'
                    
                    if file_key in files:
                        file = files[file_key]
                        if file and file.filename != '' and allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                            temp_agenda_items.append({
                                'form_display_number': current_idx_form, # The number shown on the form
                                'file_object': file
                            })
                        elif file and file.filename != '':
                             flash(f"ไฟล์ '{file.filename}' สำหรับวาระที่ {current_idx_form} ไม่ใช่ประเภท PDF หรือมีปัญหา", "warning")
                             # Decide if to proceed or fail entirely
                        # If no file for a numbered item, it might be an empty agenda item slot if allowed
                    
                    processed_indices.add(current_idx_form)

                except ValueError:
                    # Handle cases where the index is not an int, though JS should ensure this
                    pass
        
        # Sort items by their form display number to maintain order
        temp_agenda_items.sort(key=lambda x: x['form_display_number'])

        # Now assign actual item_number and save files
        db_item_number_counter = 1
        for item_data in temp_agenda_items:
            file = item_data['file_object']
            original_filename = file.filename            
            stored_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1] # ให้แน่ใจว่าชื่อไฟล์ไม่ซ้ำกันสำหรับการจัดเก็บเพื่อป้องกันการเขียนทับ
            file_path = os.path.join(upload_folder_path, stored_filename)            
            try:
                file.save(file_path)
                filesize = os.path.getsize(file_path)
                agenda_files_info.append({
                    'item_number': db_item_number_counter, # Assign sequential numbers for DB storage
                    'original_filename': original_filename,
                    'stored_filename': stored_filename,
                    # เก็บเป็น path ที่จะใช้ใน Flask เช่น 'uploads/xxxx.pdf'
                    'file_url': f"{current_app.config['UPLOAD_FOLDER']}/{stored_filename}", 
                    'filesize': filesize,
                })
                db_item_number_counter += 1
            except Exception as e:
                flash(f"ไม่สามารถบันทึกไฟล์ '{original_filename}': {e}", "danger")
                # Clean up already saved files for this meeting if one fails? (more complex rollback)
                return redirect(url_for('main.index'))


        if not agenda_files_info:
            flash("กรุณาแนบไฟล์วาระการประชุมอย่างน้อยหนึ่งไฟล์", "warning")
            return redirect(url_for('main.index'))

        try:
            create_meeting_and_agendas(title, instance, meeting_date, username, agenda_files_info)
            flash("สร้างการประชุมและอัปโหลดวาระสำเร็จ", "success")
        except Exception as e:
            flash(f"เกิดข้อผิดพลาดในการบันทึกข้อมูลการประชุม: {e}", "danger")
            # Attempt to clean up saved files if DB insertion fails
            for item_info in agenda_files_info:
                full_file_path = os.path.join(upload_folder_path, item_info['stored_filename'])
                if os.path.exists(full_file_path):
                    try:
                        os.remove(full_file_path)
                    except OSError as oe:
                        current_app.logger.error(f"Error cleaning up file {full_file_path}: {oe}")


    return redirect(url_for('main.index'))


@main_bp.route('/delete_meeting/<int:meeting_id>', methods=['POST'])
@login_required(role='admin')
def delete_meeting(meeting_id):
    try:
       # รับรายการเพื่อลบไฟล์ของพวกเขา
        items_to_delete = get_agenda_items_for_meeting(meeting_id) # สอบถามก่อนลบจาก DB
        
        # ลบออกจาก DB ในการลบแบบคาสเคดใน DB ควรจัดการรายการในตาราง agenda_items
        delete_meeting_from_db(meeting_id) # ฟังก์ชันนี้ใน models.py ไม่จำเป็นต้องส่งคืนรายการอีกต่อไป

        # ลบไฟล์จริง
        upload_folder_path = os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'])
        for item in items_to_delete:
            if item.get('stored_filename'):
                file_path = os.path.join(upload_folder_path, item['stored_filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
        flash(f"ลบการประชุม ID {meeting_id} และไฟล์ที่เกี่ยวข้องสำเร็จ", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลบการประชุม ID {meeting_id}: {e}", "danger")
    return redirect(url_for('main.index'))

@main_bp.route('/delete_agenda_item/<int:item_id>', methods=['POST'])
@login_required(role='admin')
def delete_agenda_item(item_id):
    try:
        item_to_delete = delete_agenda_item_from_db(item_id) # ตอนนี้จะส่งคืนรายการหากประสบความสำเร็จ
        if item_to_delete and item_to_delete.get('stored_filename'):
            upload_folder_path = os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'])
            file_path = os.path.join(upload_folder_path, item_to_delete['stored_filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f"ลบวาระ ID {item_id} และไฟล์ที่เกี่ยวข้องสำเร็จ", "success")
        elif item_to_delete is None: # delete_agenda_item_from_db ส่งคืน None เนื่องจากไม่พบรายการ
             flash(f"ไม่พบวาระ ID {item_id} ที่ต้องการลบ", "warning")
        else: # รายการถูกลบออกจาก DB แต่บางทีอาจไม่มีชื่อไฟล์ที่จัดเก็บไว้หรือมีปัญหา
            flash(f"ลบข้อมูลวาระ ID {item_id} จากฐานข้อมูลสำเร็จ แต่มีปัญหาในการค้นหาไฟล์", "warning")

    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลบวาระ ID {item_id}: {e}", "danger")
    return redirect(url_for('main.index'))


@main_bp.route('/view_pdf/<filename>')
@login_required()
def view_pdf(filename):
    # ตรวจสอบให้แน่ใจว่าชื่อไฟล์นั้นปลอดภัยและไม่พยายามเข้าถึงไดเร็กทอรีหลัก
    # secure_filename นั้นดีสำหรับการป้อนข้อมูล แต่ในกรณีนี้ เราเชื่อถือ storage_filename จาก DB    
    if '..' in filename or filename.startswith('/'):
        flash("ชื่อไฟล์ไม่ถูกต้อง", "danger")
        return redirect(url_for('main.index'))

    upload_folder = os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'])
    
    # สำหรับการดูแบบป๊อปอัป อาจต้องใช้ 'อินไลน์' แทน 'ไฟล์แนบ'
    # การบังคับให้ดาวน์โหลด: as_attachment=True
    # สำหรับการดูในเบราว์เซอร์: as_attachment=False, mimetype='application/pdf'
    try:
        return send_from_directory(directory=upload_folder, path=filename, as_attachment=False, mimetype='application/pdf')
    except FileNotFoundError:
        flash("ไม่พบไฟล์ที่ต้องการ", "danger")
        return redirect(url_for('main.index'))

@main_bp.route('/download_pdf/<filename>')
@login_required()
def download_pdf(filename):
    if '..' in filename or filename.startswith('/'):
        flash("ชื่อไฟล์ไม่ถูกต้อง", "danger")
        return redirect(url_for('main.index'))

    upload_folder = os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'])
    item = None
    # พยายามค้นหาชื่อไฟล์ต้นฉบับจาก storage_filename หากเป็นไปได้
    # วิธีนี้ต้องใช้การค้นหา DB ซึ่งอาจจะช้า
    # วิธีที่ง่ายกว่าคือใช้ storage_filename เป็นชื่อไฟล์ดาวน์โหลด
    # เพื่อประสบการณ์ผู้ใช้ที่ดีขึ้น เราควรพยายามค้นหาชื่อไฟล์ต้นฉบับ
    # ซึ่งหมายความว่าต้องใช้ query_db สำหรับรายการที่มี storage_filename
    # ตัวอย่าง:
    # from .models import query_db
    # item_data = query_db("SELECT original_filename FROM AGENDA_ITEMS WHERE stored_filename = :sfn", {'sfn': filename}, one=True)
    # download_name = item_data['original_filename'] if item_data else filename

    try:
        # For this example, we'll just use the stored_filename as the download name.
        # If you want original filename, you need to query DB based on stored_filename.
        return send_from_directory(directory=upload_folder, path=filename, as_attachment=True)
    except FileNotFoundError:
        flash("ไม่พบไฟล์ที่ต้องการดาวน์โหลด", "danger")
        return redirect(url_for('main.index'))