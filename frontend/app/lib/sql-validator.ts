/**
 * SQL Query Validator
 * Validates SQL queries to ensure only safe DML operations are allowed
 */

// List of allowed SQL operations (case-insensitive)
const ALLOWED_OPERATIONS = ['SELECT', 'UPDATE', 'DELETE'];

// List of restricted DDL operations and keywords
const RESTRICTED_OPERATIONS = [
  'CREATE',
  'ALTER',
  'DROP',
  'TRUNCATE',
  'RENAME',
  'GRANT',
  'REVOKE',
  'ANALYZE',
  'VACUUM',
  'ATTACH',
  'DETACH',
  'PRAGMA',
  'REINDEX',
  'SAVEPOINT',
  'RELEASE'
];

// Additional restricted keywords that could modify schema
const RESTRICTED_KEYWORDS = [
  'ADD COLUMN',
  'DROP COLUMN',
  'MODIFY COLUMN',
  'ADD CONSTRAINT',
  'DROP CONSTRAINT',
  'ADD INDEX',
  'DROP INDEX',
  'CREATE INDEX',
  'CREATE UNIQUE',
  'CREATE VIEW',
  'DROP VIEW',
  'CREATE TRIGGER',
  'DROP TRIGGER',
  'CREATE PROCEDURE',
  'DROP PROCEDURE',
  'CREATE FUNCTION',
  'DROP FUNCTION'
];

export interface ValidationResult {
  isValid: boolean;
  error?: string;
  operation?: string;
}

/**
 * Validates a SQL query to ensure it only contains allowed operations
 * @param query The SQL query to validate
 * @returns ValidationResult indicating if query is valid and any error message
 */
export function validateSQLQuery(query: string): ValidationResult {
  if (!query || !query.trim()) {
    return { isValid: false, error: 'Query cannot be empty' };
  }

  // Normalize the query - remove comments and extra whitespace
  const normalizedQuery = query
    .replace(/--.*$/gm, '') // Remove single-line comments
    .replace(/\/\*[\s\S]*?\*\//g, '') // Remove multi-line comments
    .replace(/\s+/g, ' ') // Replace multiple spaces with single space
    .trim()
    .toUpperCase();

  // Check for multiple statements (security risk)
  if (normalizedQuery.includes(';') && normalizedQuery.indexOf(';') < normalizedQuery.length - 1) {
    return { 
      isValid: false, 
      error: 'Multiple statements are not allowed. Please execute one query at a time.' 
    };
  }

  // Extract the first word (operation)
  const firstWord = normalizedQuery.split(' ')[0].replace(';', '');
  
  // Check if it's an allowed operation
  if (ALLOWED_OPERATIONS.includes(firstWord)) {
    // Additional check for UPDATE and DELETE - ensure they have WHERE clause (optional but recommended)
    if ((firstWord === 'UPDATE' || firstWord === 'DELETE') && !normalizedQuery.includes('WHERE')) {
      // This is just a warning - we'll still allow it but inform the user
      console.warn(`${firstWord} statement without WHERE clause detected`);
    }
    return { isValid: true, operation: firstWord };
  }

  // Check for restricted operations
  for (const restricted of RESTRICTED_OPERATIONS) {
    if (normalizedQuery.startsWith(restricted)) {
      return { 
        isValid: false, 
        error: `${restricted} operations are not allowed in the query interface. Only SELECT, UPDATE, and DELETE queries are permitted.` 
      };
    }
  }

  // Check for restricted keywords anywhere in the query
  for (const keyword of RESTRICTED_KEYWORDS) {
    if (normalizedQuery.includes(keyword)) {
      return { 
        isValid: false, 
        error: `Query contains restricted operation: ${keyword}. Only SELECT, UPDATE, and DELETE queries are permitted.` 
      };
    }
  }

  // Check for WITH statements that might contain DDL
  if (normalizedQuery.startsWith('WITH') && 
      (normalizedQuery.includes('CREATE') || normalizedQuery.includes('DROP') || normalizedQuery.includes('ALTER'))) {
    return { 
      isValid: false, 
      error: 'CTE (WITH clause) containing DDL operations is not allowed.' 
    };
  }

  // If we get here, it's an unrecognized operation
  return { 
    isValid: false, 
    error: `Unrecognized or restricted SQL operation. Only SELECT, UPDATE, and DELETE queries are permitted.` 
  };
}

/**
 * Get a user-friendly message for a validation error
 * @param result The validation result
 * @returns A formatted error message
 */
export function getValidationErrorMessage(result: ValidationResult): string {
  if (result.isValid) return '';
  
  return result.error || 'Invalid SQL query';
}