-- 1. Все мероприятия
SELECT * FROM events ORDER BY event_date;

-- 2. Активные объявления, которые показываются сегодня
SELECT title, content, end_date FROM announcements
WHERE is_active AND current_date BETWEEN start_date AND end_date;

-- 3. Мероприятия по категории (параметр: :category_id)
SELECT title, event_date, location FROM events WHERE category_id = :category_id;

-- 4. Видеоматериалы
SELECT title, file_path, created_at FROM media WHERE media_type = 'video' AND is_active;

-- 5. Мероприятия от ближайших к поздним
SELECT title, event_date FROM events ORDER BY event_date;

-- 6. Поиск материалов по названию (параметр: :search_text)
SELECT media_id, title, media_type FROM media WHERE title ILIKE '%' || :'search_text' || '%';

-- 7. Уникальные типы материалов
SELECT DISTINCT media_type FROM media ORDER BY media_type;

-- 8. Последние 10 добавленных материалов
SELECT title, created_at FROM media ORDER BY created_at DESC LIMIT 10;

-- 9. Активные объявления для аудитории абитуриентов
SELECT a.title, a.content FROM announcements a JOIN audiences au USING (audience_id)
WHERE au.name = 'Абитуриенты' AND a.is_active
  AND current_date BETWEEN a.start_date AND a.end_date;

-- 10. Пользователи
SELECT username, full_name, is_active FROM users ORDER BY full_name;

-- 11. Мероприятия с категориями
SELECT e.title, e.event_date, c.name AS category
FROM events e JOIN categories c USING (category_id);

-- 12. Мероприятия с организаторами
SELECT e.title, e.event_date, u.full_name AS organizer
FROM events e JOIN users u ON u.user_id = e.organizer_id;

-- 13. Количество мероприятий в каждой категории, включая пустые
SELECT c.name, count(e.event_id) AS event_count
FROM categories c LEFT JOIN events e USING (category_id)
GROUP BY c.category_id, c.name ORDER BY event_count DESC, c.name;

-- 14. Количество материалов по типу
SELECT media_type, count(*) AS total FROM media GROUP BY media_type ORDER BY media_type;

-- 15. Количество элементов в каждом плейлисте
SELECT p.name, count(pi.item_id) AS item_count
FROM playlists p LEFT JOIN playlist_items pi USING (playlist_id)
GROUP BY p.playlist_id, p.name ORDER BY p.name;

-- 16. Объявления с целевой аудиторией и автором
SELECT a.title, a.start_date, au.name AS audience, u.full_name AS author
FROM announcements a JOIN audiences au USING (audience_id)
JOIN users u ON u.user_id = a.author_id;

-- 17. Категории, где число мероприятий выше среднего по категориям
WITH counts AS (
  SELECT c.category_id, c.name, count(e.event_id) AS event_count
  FROM categories c LEFT JOIN events e USING (category_id)
  GROUP BY c.category_id, c.name
)
SELECT name, event_count FROM counts
WHERE event_count > (SELECT avg(event_count) FROM counts)
ORDER BY event_count DESC;

-- 18. Наиболее используемые источники материалов
SELECT s.name, count(m.media_id) AS media_count
FROM sources s JOIN media m USING (source_id)
GROUP BY s.source_id, s.name HAVING count(m.media_id) > 3
ORDER BY media_count DESC, s.name;

-- 19. Активные материалы, включённые в активный плейлист
SELECT m.title, m.media_type
FROM media m
WHERE m.is_active AND EXISTS (
  SELECT 1 FROM playlist_items pi JOIN playlists p USING (playlist_id)
  WHERE pi.media_id = m.media_id AND p.is_active
);

-- 20. Пять пользователей, добавивших наибольшее число материалов
SELECT u.username, u.full_name, count(m.media_id) AS added_media
FROM users u JOIN media m ON m.added_by = u.user_id
GROUP BY u.user_id, u.username, u.full_name
ORDER BY added_media DESC, u.username LIMIT 5;

-- Удобное представление для выбора расписания, действующего в текущий момент.
-- При пересекающихся слотах будет выбрано наиболее позднее время начала.
SELECT s.name AS schedule_name, d.name AS display_name, p.name AS playlist_name
FROM schedules s JOIN displays d USING (display_id) JOIN playlists p USING (playlist_id)
WHERE s.is_active AND d.is_active AND p.is_active
  AND current_date BETWEEN s.start_date AND s.end_date
  AND localtime BETWEEN s.start_time AND s.end_time
ORDER BY s.start_time DESC LIMIT 1;
