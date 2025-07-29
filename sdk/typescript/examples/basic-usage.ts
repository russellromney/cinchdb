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

    // Switch to the new branch
    await client.switchBranch('feature-branch');

    // Create a table
    await client.createTable({
      name: 'products',
      columns: [
        { name: 'name', type: 'TEXT', nullable: false },
        { name: 'description', type: 'TEXT', nullable: true },
        { name: 'price', type: 'REAL', nullable: false },
        { name: 'in_stock', type: 'INTEGER', nullable: false, default: '1' },
      ],
    });

    // Insert some data
    const product = await client.insert('products', {
      name: 'Widget',
      description: 'A useful widget',
      price: 29.99,
      in_stock: 100,
    });
    console.log('Created product:', product);

    // Query data
    const result = await client.query('SELECT * FROM products WHERE price < ?', [50]);
    console.log('Query results:', result.data);

    // Update a record
    const updated = await client.update('products', product.id!, {
      price: 24.99,
    });
    console.log('Updated product:', updated);

    // Create a view
    await client.createView({
      name: 'affordable_products',
      sql: 'SELECT * FROM products WHERE price < 100',
      description: 'Products under $100',
    });

    // List views
    const views = await client.listViews();
    console.log('Views:', views);

    // Check if we can merge back to main
    const mergeCheck = await client.canMergeBranches('feature-branch', 'main');
    console.log('Can merge:', mergeCheck);

    if (mergeCheck.can_merge) {
      // Merge changes back to main
      const mergeResult = await client.mergeIntoMain('feature-branch');
      console.log('Merge result:', mergeResult);
    }

    // Switch context to different tenant
    const tenantClient = client.switchTenant('customer_a');
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