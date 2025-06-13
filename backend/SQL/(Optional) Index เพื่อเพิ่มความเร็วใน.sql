-- (Optional) Index เพื่อเพิ่มความเร็วในการค้นหา
CREATE INDEX idx_meeting_date ON MEETINGS(meeting_date);
CREATE INDEX idx_agenda_meeting_id ON AGENDA_ITEMS(meeting_id);