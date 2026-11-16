BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO roles(role_id, role_name, description) VALUES
 (1, 'admin', 'Полный доступ к системе'),
 (2, 'editor', 'Подготовка и редактирование материалов');

INSERT INTO users(user_id, username, password_hash, full_name, role_id, created_at, is_active) VALUES
 (1,'admin', crypt('ChangeMe-Admin-2026', gen_salt('bf', 12)),'Администратор системы',1,now()-interval '2 years',true),
 (2,'editor.ivanova',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Мария Иванова',2,now()-interval '330 days',true),
 (3,'editor.petrov',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Алексей Петров',2,now()-interval '300 days',true),
 (4,'editor.sidorova',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Елена Сидорова',2,now()-interval '270 days',true),
 (5,'editor.smirnov',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Дмитрий Смирнов',2,now()-interval '240 days',true),
 (6,'editor.kuznetsova',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Анна Кузнецова',2,now()-interval '210 days',true),
 (7,'editor.orlov',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Илья Орлов',2,now()-interval '180 days',true),
 (8,'editor.volkova',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Ольга Волкова',2,now()-interval '150 days',true),
 (9,'editor.morozov',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Никита Морозов',2,now()-interval '120 days',true),
 (10,'editor.fedorova',crypt('ChangeMe-Editor-2026',gen_salt('bf',12)),'Ирина Фёдорова',2,now()-interval '90 days',true);

INSERT INTO categories(category_id,name,description) VALUES
 (1,'Студенческая жизнь','События и повседневная жизнь студентов'),
 (2,'Научная деятельность','Конференции, семинары и исследования'),
 (3,'Мероприятия кафедры','События, организованные кафедрой'),
 (4,'Достижения студентов','Награды и результаты студентов'),
 (5,'Преподавательский состав','Новости и материалы о преподавателях'),
 (6,'Абитуриентам','Информация для поступающих'),
 (7,'Объявления','Официальная информация кафедры'),
 (8,'Культура и спорт','Культурные и спортивные события');

INSERT INTO sources(source_id,name,source_type,url,description) VALUES
 (1,'Официальный сайт ДонГУ','website','https://donnu.ru','Официальный сайт университета'),
 (2,'Группа кафедры ВКонтакте','social','https://vk.com/','Публикации кафедры в социальной сети'),
 (3,'Материалы студентов','internal',NULL,'Материалы, предоставленные студентами'),
 (4,'Материалы преподавателей','internal',NULL,'Материалы, предоставленные преподавателями'),
 (5,'Кафедра ДонГУ','internal','https://donnu.ru','Собственные материалы кафедры');

INSERT INTO audiences(audience_id,name,description) VALUES
 (1,'Студенты','Обучающиеся кафедры'),
 (2,'Абитуриенты','Поступающие и будущие студенты'),
 (3,'Сотрудники','Преподаватели и сотрудники университета');

INSERT INTO events(event_id,title,description,event_date,location,status,organizer_id,category_id) VALUES
 (1,'День открытых дверей','Знакомство с образовательными программами',now()+interval '14 days','Главный корпус, зал 2','planned',2,6),
 (2,'Научный семинар по цифровым системам','Доклады молодых исследователей',now()-interval '60 days','Аудитория 214','completed',3,2),
 (3,'Конференция молодых учёных','Межвузовская научная конференция',now()+interval '30 days','Конференц-зал','planned',4,2),
 (4,'Посвящение в студенты','Встреча первокурсников',now()-interval '120 days','Актовый зал','completed',5,1),
 (5,'Олимпиада кафедры','Студенческая предметная олимпиада',now()+interval '45 days','Лаборатория 3','planned',6,4),
 (6,'Встреча выпускников','Встреча выпускников и преподавателей',now()-interval '20 days','Аудитория 101','completed',7,3),
 (7,'Мастер-класс по анализу данных','Практический мастер-класс',now()+interval '7 days','Компьютерный класс','planned',8,2),
 (8,'День кафедры','Праздничная программа кафедры',now()-interval '200 days','Холл кафедры','completed',9,3),
 (9,'Экскурсия по лабораториям','Знакомство с лабораториями',now()+interval '21 days','Лабораторный корпус','planned',10,6),
 (10,'Студенческий турнир','Турнир между учебными группами',now()-interval '35 days','Спортивный зал','completed',2,8),
 (11,'Защита учебных проектов','Презентация проектов студентов',now()+interval '10 days','Аудитория 312','planned',3,1),
 (12,'Круглый стол преподавателей','Обсуждение учебных практик',now()-interval '80 days','Аудитория 205','completed',4,5),
 (13,'Конкурс научных постеров','Выставка исследовательских работ',now()+interval '60 days','Библиотека','planned',5,4),
 (14,'Практикум для абитуриентов','Открытое занятие для поступающих',now()+interval '90 days','Лаборатория 1','planned',6,6),
 (15,'Волонтёрская акция','Студенческая добровольческая акция',now()-interval '12 days','Кампус','completed',7,1);

INSERT INTO media(media_id,title,description,media_type,file_path,created_at,is_active,added_by,category_id,source_id,event_id)
SELECT g,
       (ARRAY['Открытый день — аудитория','Семинар — докладчики','Конференция — регистрация','Первокурсники на встрече','Олимпиада — участники',
       'Выпускники кафедры','Практикум по данным','Праздник кафедры','Лабораторный корпус','Студенческий турнир',
       'Защита проектов','Круглый стол','Научные постеры','Практикум абитуриентов','Волонтёрская акция',
       'Студенческая команда','Лабораторная работа','Преподаватели кафедры','Университетский кампус','Исследовательский проект',
       'Студенческая жизнь','Открытая лекция','Конкурс проектов','Учебная лаборатория','Кафедральная встреча'])[g],
       'Тестовая карточка медиаматериала для демонстрации связей БД',
       CASE WHEN g IN (2,7,11,16,20,24) THEN 'video' ELSE 'image' END,
       CASE WHEN g IN (2,7,11,16,20,24) THEN format('media/videos/demo_%s.mp4',lpad(g::text,2,'0'))
            ELSE format('media/images/demo_%s.jpg',lpad(g::text,2,'0')) END,
       now()-make_interval(days=>g*3),true,((g-1)%9)+2,((g-1)%8)+1,((g-1)%5)+1,((g-1)%15)+1
FROM generate_series(1,25) AS g;

INSERT INTO announcements(announcement_id,title,content,start_date,end_date,is_active,author_id,category_id,audience_id) VALUES
 (1,'День открытых дверей — регистрация','Приглашаем будущих абитуриентов познакомиться с кафедрой.',current_date-2,current_date+30,true,2,6,2),
 (2,'Приём заявок на олимпиаду','Подайте заявку на участие через учебную часть.',current_date-5,current_date+20,true,3,4,1),
 (3,'Научная конференция кафедры','Открыта регистрация докладчиков и слушателей.',current_date,current_date+45,true,4,2,1),
 (4,'Изменение аудитории семинара','Семинар состоится в аудитории 214.',current_date-10,current_date+2,true,5,7,1),
 (5,'Консультации преподавателей','Расписание консультаций опубликовано на кафедре.',current_date-3,current_date+14,true,6,5,1),
 (6,'Защита учебных проектов','Порядок выступлений будет размещён дополнительно.',current_date+1,current_date+18,true,7,1,1),
 (7,'Практикум для поступающих','Запись на открытое занятие доступна абитуриентам.',current_date-1,current_date+60,true,8,6,2),
 (8,'График работы кафедры','Актуальный график приёма сотрудников.',current_date-20,current_date+10,true,9,7,3),
 (9,'Конкурс научных постеров','Принимаются работы студентов всех курсов.',current_date+5,current_date+55,true,10,4,1),
 (10,'Встреча выпускников','Просим подтвердить участие до конца месяца.',current_date-12,current_date+12,true,2,3,3),
 (11,'Волонтёрская акция кампуса','Приглашаем студентов присоединиться к акции.',current_date-7,current_date+7,true,3,8,1),
 (12,'Архивное объявление','Информация о прошедшем мероприятии.',current_date-90,current_date-60,false,4,7,1);

INSERT INTO playlists(playlist_id,name,description,created_by,is_active,created_at) VALUES
 (1,'Информация для студентов','Учебные новости, события и материалы студентов',2,true,now()-interval '40 days'),
 (2,'Для абитуриентов','Материалы о поступлении и кафедре',3,true,now()-interval '35 days'),
 (3,'Новости кафедры','Актуальные объявления и мероприятия',4,true,now()-interval '30 days'),
 (4,'Научная деятельность','Конференции, семинары и проекты',5,true,now()-interval '25 days'),
 (5,'Архив демонстрации','Неактивный тестовый плейлист',6,false,now()-interval '20 days');

-- 30 ordered entries; each entry references exactly one media/event/announcement.
INSERT INTO playlist_items(item_id,playlist_id,position,display_duration,media_id,announcement_id,event_id)
SELECT g,((g-1)%5)+1,((g-1)/5)+1,
       CASE WHEN g%3=0 THEN 20 ELSE 12 END,
       CASE WHEN g%3=1 THEN ((g-1)%25)+1 END,
       CASE WHEN g%3=2 THEN ((g-1)%12)+1 END,
       CASE WHEN g%3=0 THEN ((g-1)%15)+1 END
FROM generate_series(1,30) AS g;

INSERT INTO displays(display_id,name,location,description,is_active) VALUES
 (1,'Телевизор в холле кафедры','Холл кафедры','Основной демонстрационный экран',true);

INSERT INTO schedules(schedule_id,name,playlist_id,display_id,start_date,end_date,start_time,end_time,is_active) VALUES
 (1,'Утренний показ студентов',1,1,current_date,current_date+180,'08:00','10:00',true),
 (2,'Информация для абитуриентов',2,1,current_date,current_date+180,'10:00','12:00',true),
 (3,'Новости кафедры',3,1,current_date,current_date+180,'12:00','14:00',true),
 (4,'Научный блок',4,1,current_date,current_date+180,'14:00','17:00',true),
 (5,'Архивное расписание',5,1,current_date-365,current_date-180,'17:00','18:00',false);

SELECT setval(pg_get_serial_sequence('roles','role_id'),(SELECT max(role_id) FROM roles));
SELECT setval(pg_get_serial_sequence('users','user_id'),(SELECT max(user_id) FROM users));
SELECT setval(pg_get_serial_sequence('categories','category_id'),(SELECT max(category_id) FROM categories));
SELECT setval(pg_get_serial_sequence('sources','source_id'),(SELECT max(source_id) FROM sources));
SELECT setval(pg_get_serial_sequence('audiences','audience_id'),(SELECT max(audience_id) FROM audiences));
SELECT setval(pg_get_serial_sequence('events','event_id'),(SELECT max(event_id) FROM events));
SELECT setval(pg_get_serial_sequence('media','media_id'),(SELECT max(media_id) FROM media));
SELECT setval(pg_get_serial_sequence('announcements','announcement_id'),(SELECT max(announcement_id) FROM announcements));
SELECT setval(pg_get_serial_sequence('playlists','playlist_id'),(SELECT max(playlist_id) FROM playlists));
SELECT setval(pg_get_serial_sequence('playlist_items','item_id'),(SELECT max(item_id) FROM playlist_items));
SELECT setval(pg_get_serial_sequence('displays','display_id'),(SELECT max(display_id) FROM displays));
SELECT setval(pg_get_serial_sequence('schedules','schedule_id'),(SELECT max(schedule_id) FROM schedules));

COMMIT;
