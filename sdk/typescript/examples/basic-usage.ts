/**
 * CinchDB TypeScript SDK - Basic Usage Example
 */

import { CinchDBClient } from '../src';

async function main() {
  // Initialize client
  const client = new CinchDBClient({
    apiUrl: 'http://localhost:8000',
    apiKey: 'your-api-key-here',
    database: 'myapp',
    branch: 'main',
    tenant: 'main',
  });

  try {
    // Get project info
    const projectInfo = await client.getProjectInfo();
    console.log('Project Info:', projectInfo);

    // List databases
    const databases = await client.listDatabases();
    console.log('Databases:', databases);

    // Create a new branch
    await client.createBranch({
      name: 'feature-branch',
      source: 'main',
    });

    // Create new client instance for the feature branch
    const featureClient = new CinchDBClient({
      ...client.config,
      branch: 'feature-branch',
    });

    // Create tables with foreign keys
    await featureClient.createTable({
      name: 'categories',
      columns: [
        { name: 'name', type: 'TEXT', nullable: false },
        { name: 'description', type: 'TEXT', nullable: true },
      ],
    });

    await featureClient.createTable({
      name: 'products',
      columns: [
        { name: 'name', type: 'TEXT', nullable: false },
        { name: 'description', type: 'TEXT', nullable: true },
        { name: 'price', type: 'REAL', nullable: false },
        { name: 'in_stock', type: 'INTEGER', nullable: false, default: '1' },
        { 
          name: 'category_id', 
          type: 'TEXT', 
          nullable: true,
          foreign_key: {
            table: 'categories',
            on_delete: 'SET NULL'
          }
        },
      ],
    });

    // Insert some data
    const product = await featureClient.insert('products', {
      name: 'Widget',
      description: 'A useful widget',
      price: 29.99,
      in_stock: 100,
    });
    console.log('Created product:', product);

    // Query data
    const result = await featureClient.query('SELECT * FROM products WHERE price < ?', [50]);
    console.log('Query results:', result.data);

    // Update a record
    const updated = await featureClient.update('products', product.id!, {
      price: 24.99,
    });
    console.log('Updated product:', updated);

    // Create a view
    await featureClient.createView({
      name: 'affordable_products',
      sql: 'SELECT * FROM products WHERE price < 100',
      description: 'Products under $100',
    });

    // List views
    const views = await featureClient.listViews();
    console.log('Views:', views);

    // Check if we can merge back to main
    const mergeCheck = await featureClient.canMergeBranches('feature-branch', 'main');
    console.log('Can merge:', mergeCheck);

    if (mergeCheck.can_merge) {
      // Merge changes back to main
      const mergeResult = await featureClient.mergeIntoMain('feature-branch');
      console.log('Merge result:', mergeResult);
    }

    // Create new client instance for different tenant
    const tenantClient = new CinchDBClient({
      ...client.config,
      tenant: 'customer_a',
    });
    const tenantData = await tenantClient.query('SELECT COUNT(*) as count FROM products');
    console.log('Tenant data:', tenantData.data);

  } catch (error) {
    console.error('Error:', error);
  }
}

// Run if this file is executed directly
if (require.main === module) {
  main();
}