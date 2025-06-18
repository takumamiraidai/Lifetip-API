import sqlite3
import os

def migrate_database():
    """データベースに必要なカラムを追加するマイグレーション"""
    db_path = os.path.join(os.getcwd(), "app.db")
    print(f"Migrating database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 既存のテーブル構造を確認
    cursor.execute("PRAGMA table_info(agents)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"Current columns: {column_names}")
    
    # voice_typeカラムの追加
    if 'voice_type' not in column_names:
        print("Adding voice_type column")
        cursor.execute("ALTER TABLE agents ADD COLUMN voice_type TEXT DEFAULT 'voicevox'")
    else:
        print("voice_type column already exists")
    
    # has_custom_voiceカラムの追加
    if 'has_custom_voice' not in column_names:
        print("Adding has_custom_voice column")
        cursor.execute("ALTER TABLE agents ADD COLUMN has_custom_voice INTEGER DEFAULT 0")
    else:
        print("has_custom_voice column already exists")
    
    # voice_speaker_idカラムの追加
    if 'voice_speaker_id' not in column_names:
        print("Adding voice_speaker_id column")
        cursor.execute("ALTER TABLE agents ADD COLUMN voice_speaker_id INTEGER DEFAULT 1")
    else:
        print("voice_speaker_id column already exists")
    
    # 変更を保存
    conn.commit()
    
    # マイグレーション後のテーブル構造を確認
    cursor.execute("PRAGMA table_info(agents)")
    updated_columns = cursor.fetchall()
    updated_column_names = [col[1] for col in updated_columns]
    print(f"Updated columns: {updated_column_names}")
    
    # サンプルデータの確認
    cursor.execute("SELECT * FROM agents LIMIT 1")
    sample_row = cursor.fetchone()
    if sample_row:
        print("Sample row after migration:")
        for i, col in enumerate(updated_column_names):
            if i < len(sample_row):
                print(f"  {col}: {sample_row[i]}")
    
    conn.close()
    print("Migration completed")

if __name__ == "__main__":
    migrate_database()
