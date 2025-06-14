-- ตารางการประชุมหลัก
CREATE TABLE MEETINGS (
    meeting_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
    title VARCHAR2(255) NOT NULL,
    meeting_instance VARCHAR2(50), -- เช่น 1/2568
    meeting_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by VARCHAR2(50) -- เก็บ username ของผู้อัปโหลด
);