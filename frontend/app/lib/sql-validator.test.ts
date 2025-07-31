import { validateSQLQuery, getValidationErrorMessage } from './sql-validator';

describe('SQL Query Validator', () => {
  describe('validateSQLQuery', () => {
    // Test allowed operations
    test('should allow SELECT queries', () => {
      const queries = [
        'SELECT * FROM users',
        'select id, name from products',
        'SELECT COUNT(*) FROM orders WHERE status = "pending"',
        'SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id'
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(true);
        expect(result.operation).toBe('SELECT');
      });
    });

    test('should allow UPDATE queries', () => {
      const queries = [
        'UPDATE users SET name = "John" WHERE id = 1',
        'update products set price = 100 where category = "electronics"',
        'UPDATE orders SET status = "completed"' // Without WHERE - should still be valid
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(true);
        expect(result.operation).toBe('UPDATE');
      });
    });

    test('should allow DELETE queries', () => {
      const queries = [
        'DELETE FROM users WHERE id = 1',
        'delete from products where stock = 0',
        'DELETE FROM logs' // Without WHERE - should still be valid
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(true);
        expect(result.operation).toBe('DELETE');
      });
    });

    // Test restricted operations
    test('should block CREATE operations', () => {
      const queries = [
        'CREATE TABLE users (id INTEGER PRIMARY KEY)',
        'CREATE INDEX idx_users_name ON users(name)',
        'CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1',
        'CREATE TRIGGER update_timestamp BEFORE UPDATE ON users'
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(false);
        expect(result.error).toContain('CREATE');
      });
    });

    test('should block ALTER operations', () => {
      const queries = [
        'ALTER TABLE users ADD COLUMN email TEXT',
        'ALTER TABLE products DROP COLUMN description',
        'ALTER TABLE orders RENAME TO order_history'
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(false);
        expect(result.error).toContain('ALTER');
      });
    });

    test('should block DROP operations', () => {
      const queries = [
        'DROP TABLE users',
        'DROP INDEX idx_users_name',
        'DROP VIEW active_users',
        'DROP DATABASE mydb'
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(false);
        expect(result.error).toContain('DROP');
      });
    });

    test('should block TRUNCATE operations', () => {
      const result = validateSQLQuery('TRUNCATE TABLE users');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('TRUNCATE');
    });

    // Test edge cases
    test('should handle queries with comments', () => {
      const queries = [
        '-- This is a comment\nSELECT * FROM users',
        '/* Multi-line\n   comment */\nSELECT * FROM products',
        'SELECT * FROM users -- WHERE id = 1'
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(true);
      });
    });

    test('should block multiple statements', () => {
      const result = validateSQLQuery('SELECT * FROM users; DROP TABLE users;');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('Multiple statements');
    });

    test('should handle empty queries', () => {
      const result = validateSQLQuery('');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('empty');
    });

    test('should handle whitespace-only queries', () => {
      const result = validateSQLQuery('   \n\t  ');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('empty');
    });

    test('should block queries with restricted keywords', () => {
      const queries = [
        'SELECT * FROM users WHERE name IN (SELECT name FROM (CREATE TABLE temp AS SELECT * FROM users))',
        'UPDATE users SET name = (SELECT name FROM users WHERE id IN (DROP TABLE products))'
      ];
      
      queries.forEach(query => {
        const result = validateSQLQuery(query);
        expect(result.isValid).toBe(false);
      });
    });

    test('should block CTE with DDL operations', () => {
      const result = validateSQLQuery('WITH temp AS (CREATE TABLE test AS SELECT * FROM users) SELECT * FROM temp');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('CTE');
    });
  });

  describe('getValidationErrorMessage', () => {
    test('should return empty string for valid result', () => {
      const result = { isValid: true };
      expect(getValidationErrorMessage(result)).toBe('');
    });

    test('should return error message for invalid result', () => {
      const result = { isValid: false, error: 'Test error' };
      expect(getValidationErrorMessage(result)).toBe('Test error');
    });

    test('should return default message when no error provided', () => {
      const result = { isValid: false };
      expect(getValidationErrorMessage(result)).toBe('Invalid SQL query');
    });
  });
});