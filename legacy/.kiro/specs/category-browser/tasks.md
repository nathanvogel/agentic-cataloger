# Implementation Plan

- [x] 1. Set up backend API infrastructure
  - Install required NestJS packages (@nestjs/swagger, class-validator, class-transformer)
  - Configure Swagger/OpenAPI in main.ts with document builder and CORS
  - Verify OpenAPI spec is accessible at /api/docs and /api/docs-json
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2. Create backend DTOs with OpenAPI decorators
  - Create CategoryResponseDto with all database fields and @ApiProperty decorators
  - Create ProductResponseDto with all database fields and @ApiProperty decorators
  - Add proper TypeScript types and nullable annotations
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2_

- [x] 3. Implement Categories Service
  - Create CategoriesService class with dependency injection
  - Implement getAllCategories() method using CategoryRepository
  - Implement getCategoryProducts() method using ProductsRepository
  - Add category existence validation in getCategoryProducts()
  - Map database results to DTO format
  - Add error handling and logging
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 8.1, 8.2, 8.5_

- [x] 4. Update ProductsRepository to return all fields
  - Modify getProductsByCategory() to select all columns instead of specific ones
  - Add ordering by name for consistent results
  - _Requirements: 2.2_

- [x] 5. Implement Categories Controller
  - Create CategoriesController with @ApiTags decorator
  - Implement GET /api/categories endpoint with Swagger decorators
  - Implement GET /api/categories/:id/products endpoint with Swagger decorators
  - Add @ApiOperation, @ApiResponse, and @ApiParam decorators
  - Wire service dependency
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Create and wire Categories Module
  - Create CategoriesModule with imports, controllers, and providers
  - Import DatabaseModule for repository access
  - Export CategoriesService if needed
  - Update AppModule to import CategoriesModule
  - _Requirements: 1.1, 2.1_

- [x] 7. Set up frontend type generation
  - Install openapi-typescript as dev dependency
  - Add generate:api script to package.json
  - Start backend server
  - Run type generation script to create backend-schema.d.ts
  - Verify generated types are correct
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 8. Configure frontend API client
  - Update app/schema/api.ts to import generated types
  - Configure fetchClient with proper baseUrl from environment
  - Export configured $api client with type safety
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 9. Create basic category browser UI on landing page
  - Update app/routes/landingpage.tsx to show category browser
  - Use $api.useQuery hook to fetch categories
  - Display categories as simple list or cards with displayName and productCount
  - Add click handler to select a category and show its products
  - Implement loading and error states
  - Use proper TypeScript types from generated schema
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 10. Add product display to landing page
  - When category is selected, fetch products using $api.useQuery
  - Display products in simple list format with key fields: name, supermarket, price, unit
  - Show attributes as JSON or simple key-value pairs
  - Display confidence score if available
  - Add back/clear button to return to category list
  - Handle loading and error states for products
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 11. Manual testing and verification
  - Start backend and verify OpenAPI docs at /api/docs
  - Verify /api/categories returns all categories with all fields
  - Verify /api/categories/:id/products returns all products with all fields
  - Verify 404 error for non-existent category
  - Start frontend and verify type generation works
  - Verify landing page displays categories
  - Verify clicking category shows products
  - Verify products display all relevant information
  - Verify back button returns to category list
  - Verify error and loading states work
  - _Requirements: All_
