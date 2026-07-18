#!/usr/bin/env python3
"""清空表 + 修正列类型，输出到文件"""
import pymysql

with open("f:\\myself\\github\\WeAgentChat\\temp\\legado\\.trae\\skills\\legado-source-creator\\scripts\\alter_result.txt", "w") as f:
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='200868', database='legado_sources')
    cur = conn.cursor()
    
    cur.execute('SET FOREIGN_KEY_CHECKS=0')
    cur.execute('TRUNCATE TABLE debug_result')
    cur.execute('TRUNCATE TABLE source')
    cur.execute('SET FOREIGN_KEY_CHECKS=1')
    f.write('TRUNCATED\n')
    
    stmts = [
        'ALTER TABLE source MODIFY COLUMN source_url MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN source_name MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN source_icon MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN source_group MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN login_url MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN login_check_js MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN login_ui MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN book_url_pattern MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN explore_url MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN explore_screen MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN cover_decode_js MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_search MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_toc MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_explore MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_content MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_book_info MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_articles MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_title MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_image MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_link MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_next_page MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_pub_date MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN rule_description MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN domain_key MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN source_json MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN search_url MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN test_detail MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN device_jar_diff MEDIUMTEXT',
        'ALTER TABLE source MODIFY COLUMN notes MEDIUMTEXT',
    ]
    for s in stmts:
        try:
            cur.execute(s)
            f.write(f'OK: {s}\n')
        except Exception as e:
            f.write(f'SKIP: {s} -> {e}\n')
    
    conn.commit()
    
    cur.execute('SHOW COLUMNS FROM source LIKE "source_icon"')
    row = cur.fetchone()
    f.write(f'icon_type={row[1]}\n')
    
    cur.execute('SELECT COUNT(*) FROM source')
    f.write(f'rows={cur.fetchone()[0]}\n')
    
    conn.close()
    f.write('DONE\n')
