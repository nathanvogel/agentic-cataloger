# Design Document

## Overview

The Category Browser is a minimal web interface for exploring product categories and their associated products. It consists of two main views: a category list page and a product list page. The backend provides RESTful API endpoints using NestJS with OpenAPI/Swagger documentation, while the frontend uses React Router and Material-UI with a type-safe API client generated from the OpenAPI spec.

This design prioritizes simplicity and rapid prototyping while establishing a solid foundation for type-safe API communication.

## Architecture

### System Components

```
┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐
│                 │  HTTP   │                 │   SQL   │              │
│  Frontend UI    │────────▶│  Backend API    │────────▶│  PostgreSQL  │
│  (React)        │◀────────│  (NestJS)       │◀────────│              │
│                 │  JSON   │                 │         │              │
└─────────────────┘         └─────────────────┘         └──────────────┘
        │                           │
        │                           │
        │                           ▼
        │                   ┌──────────────┐
        │                   │   OpenAPI    │
        │                   │     Spec     │
        │                   └──────────────┘
        │                           │
        └───────────────────────────┘
           Type-safe client
```

### Technology Stack

**Backend:**

- NestJS framework with existing module structure
- Zapatos for type-safe database queries
- Existing CategoryRepository and ProductsRepository
- @nestjs/swagger for OpenAPI spec generation
- class-validator and class-transformer for DTO validation

**Frontend:**

- React Router v7 (already configured)
- Material-UI (already configured)
- openapi-fetch and openapi-react-query for type-safe API client (already configured)
- openapi-typescript for generating TypeScript types from OpenAPI spec

### OpenAPI Workflow

1. Backend defines DTOs with Swagger decorators
2. Backend generates OpenAPI spec at `/api/docs-json`
3. Frontend runs script to fetch spec and generate TypeScript types
4. Frontend uses generated types with openapi-fetch client
5. Full type safety from backend to frontend

## Components and Interfaces

### Backend Components

#### 1. Categories Module

**Location:** `backend/src/categories/`

**Purpose:** Encapsulate category-related business logic and API endpoints

**Structure:**

```
src/categories/
├── categories.module.ts
├── categories.controller.ts
├── categories.service.ts
└── dto/
    ├── category-response.dto.ts
    └── product-response.dto.ts
```

#### 2. Categories Controller

**Endpoints:**

```typescript
@ApiTags('categories')
@Controller('api/categories')
export class CategoriesController {

  @Get()
  @ApiOperation({ summary: 'Get all categories' })
  @ApiResponse({ status: 200, type: [CategoryResponseDto] })
  async getAllCategories(): Promise<CategoryResponseDto[]>
  // Returns all categories ordered by product_count DESC

  @Get(':id/products')
  @ApiOperation({ summary: 'Get products for a category' })
  @ApiParam({ name: 'id', type: 'number' })
  @ApiResponse({ status: 200, type: [ProductResponseDto] })
  @ApiResponse({ status: 404, description: 'Category not found' })
  async getCategoryProducts(@Param('id') id: number): Promise<ProductResponseDto[]>
  // Returns all products for a specific category
}
```

#### 3. Categories Service

**Methods:**

```typescript
@Injectable()
export class CategoriesService {
  async getAllCategories(): Promise<CategoryResponseDto[]>;
  // Fetches categories from CategoryRepository
  // Maps all DB fields to DTO format

  async getCategoryProducts(categoryId: number): Promise<ProductResponseDto[]>;
  // Validates category exists
  // Fetches products from ProductsRepository
  // Maps all DB fields to DTO format
}
```

#### 4. Data Transfer Objects (DTOs)

**CategoryResponseDto:**

```typescript
export class CategoryResponseDto {
  @ApiProperty({ description: "Category ID" })
  id: number;

  @ApiProperty({ description: "Internal category name (kebab-case)" })
  name: string;

  @ApiProperty({ description: "Display name for UI" })
  displayName: string;

  @ApiProperty({ description: "Number of products in category" })
  productCount: number;

  @ApiProperty({ description: "LLM reasoning for category", nullable: true })
  reasoning: string | null;

  @ApiProperty({ description: "Confidence score (0-1)", nullable: true })
  confidence: number | null;

  @ApiProperty({ description: "Linked schema ID", nullable: true })
  schemaId: number | null;

  @ApiProperty({ description: "Creation timestamp" })
  createdAt: Date;

  @ApiProperty({ description: "Last update timestamp" })
  updatedAt: Date;
}
```

**ProductResponseDto:**

```typescript
export class ProductResponseDto {
  @ApiProperty({ description: "Product ID" })
  id: number;

  @ApiProperty({ description: "Product name" })
  name: string;

  @ApiProperty({ description: "Supermarket name" })
  supermarket: string;

  @ApiProperty({ description: "Price in CHF", nullable: true })
  price: number | null;

  @ApiProperty({ description: 'Unit (e.g., "500g", "1L")', nullable: true })
  unit: string | null;

  @ApiProperty({ description: "Unit price", nullable: true })
  unitPrice: number | null;

  @ApiProperty({ description: "Price text from source", nullable: true })
  priceText: string | null;

  @ApiProperty({ description: "Has discount flag", nullable: true })
  hasDiscount: boolean | null;

  @ApiProperty({ description: "Discount information", nullable: true })
  discountInfo: string | null;

  @ApiProperty({ description: "Product image URL", nullable: true })
  imageUrl: string | null;

  @ApiProperty({ description: "Product page URL", nullable: true })
  url: string | null;

  @ApiProperty({ description: "Source URL", nullable: true })
  scrapedFrom: string | null;

  @ApiProperty({ description: "Original categories from CSV", type: [String] })
  categories: string[];

  @ApiProperty({ description: "Extracted attributes (JSONB)", type: "object" })
  attributes: Record<string, any>;

  @ApiProperty({ description: "Assigned category ID", nullable: true })
  categoryId: number | null;

  @ApiProperty({
    description: "Categorization confidence (0-1)",
    nullable: true,
  })
  categorizationConfidence: number | null;

  @ApiProperty({
    description: "Attributes extraction timestamp",
    nullable: true,
  })
  attributesExtractedAt: Date | null;

  @ApiProperty({ description: "Scraping timestamp" })
  scrapedAt: Date;

  @ApiProperty({ description: "Creation timestamp" })
  createdAt: Date;

  @ApiProperty({ description: "Last update timestamp" })
  updatedAt: Date;
}
```

#### 5. Swagger Configuration

**Location:** `backend/src/main.ts`

```typescript
import { SwaggerModule, DocumentBuilder } from "@nestjs/swagger";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Swagger setup
  const config = new DocumentBuilder()
    .setTitle("Price Comparison API")
    .setDescription("API for browsing product categories and products")
    .setVersion("1.0")
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup("api/docs", app, document);

  // Also expose JSON spec for frontend type generation
  app.use("/api/docs-json", (req, res) => {
    res.json(document);
  });

  // Enable CORS
  app.enableCors({
    origin: process.env.FRONTEND_URL || "http://localhost:5173",
    credentials: true,
  });

  await app.listen(3000);
}
```

### Frontend Components

#### 1. Type Generation Script

**Location:** `frontend/package.json`

Add script:

```json
{
  "scripts": {
    "generate:api": "openapi-typescript http://localhost:3000/api/docs-json -o app/schema/backend-schema.d.ts"
  }
}
```

#### 2. API Client Configuration

**Location:** `frontend/app/schema/api.ts`

```typescript
import createFetchClient from "openapi-fetch";
import createClient from "openapi-react-query";
import { paths } from "./backend-schema";

const fetchClient = createFetchClient<paths>({
  baseUrl: import.meta.env.VITE_BACKEND_URL || "http://localhost:3000",
  credentials: "include",
});

export const $api = createClient(fetchClient);
```

#### 3. Route Structure

**Location:** `frontend/app/routes.ts`

```typescript
export default [
  layout("routes/_layout.tsx", [
    index("routes/landingpage.tsx"),
    route("terms", "routes/terms.tsx"),
    route("categories", "routes/categories.tsx"),
    route("categories/:id", "routes/category-products.tsx"),
  ]),
] satisfies RouteConfig;
```

#### 4. Categories List Page

**Location:** `frontend/app/routes/categories.tsx`

**Purpose:** Display all categories in a grid layout

**Key Features:**

- Use openapi-react-query hooks for data fetching
- Display loading state
- Display error state
- Grid of category cards
- Click to navigate to products

**Component Structure:**

```typescript
import { $api } from "~/schema/api";

export default function CategoriesPage() {
  const {
    data: categories,
    isLoading,
    error,
  } = $api.useQuery("get", "/api/categories");

  // Render grid of CategoryCard components
}
```

#### 5. Category Card Component

**Location:** `frontend/app/domains/categories/CategoryCard.tsx`

**Purpose:** Display a single category with all available fields

**Props:**

```typescript
import { components } from "~/schema/backend-schema";

interface CategoryCardProps {
  category: components["schemas"]["CategoryResponseDto"];
  onClick: () => void;
}
```

**Visual Design:**

- Material-UI Card component
- Display name as title
- Product count as subtitle
- Show confidence score if available
- Hover effect for interactivity
- Click navigates to product list

#### 6. Category Products Page

**Location:** `frontend/app/routes/category-products.tsx`

**Purpose:** Display all products for a selected category

**Key Features:**

- Fetch products based on route parameter (category ID)
- Display category name as header
- Back button to categories list
- List/grid of product cards
- Loading and error states

**Component Structure:**

```typescript
import { useParams } from "react-router";
import { $api } from "~/schema/api";

export default function CategoryProductsPage() {
  const { id } = useParams();
  const {
    data: products,
    isLoading,
    error,
  } = $api.useQuery("get", "/api/categories/{id}/products", {
    params: { path: { id: Number(id) } },
  });

  // Render list of ProductCard components
}
```

#### 7. Product Card Component

**Location:** `frontend/app/domains/categories/ProductCard.tsx`

**Purpose:** Display a single product with all available fields

**Props:**

```typescript
import { components } from "~/schema/backend-schema";

interface ProductCardProps {
  product: components["schemas"]["ProductResponseDto"];
}
```

**Visual Design:**

- Material-UI Card component
- Product image (if available) or placeholder
- Product name
- Supermarket badge
- Price and unit
- Discount badge if hasDiscount
- Original categories as chips
- Attributes as expandable section
- Confidence score indicator
- All timestamps in readable format

## Data Models

### Backend Models (from Zapatos schema)

Already defined in database schema - DTOs will map all fields from these tables.

### Frontend Models

Frontend will use types generated from OpenAPI spec:

```typescript
import { components } from "~/schema/backend-schema";

export type Category = components["schemas"]["CategoryResponseDto"];
export type Product = components["schemas"]["ProductResponseDto"];
```

## Error Handling

### Backend Error Handling

**Not Found Errors:**

```typescript
if (!category) {
  throw new NotFoundException(`Category with ID ${id} not found`);
}
```

**Database Errors:**

```typescript
try {
  return await this.categoryRepository.getAllCategories();
} catch (error) {
  this.logger.error("Failed to fetch categories", error);
  throw new InternalServerErrorException("Failed to fetch categories");
}
```

**Global Exception Filter:**

- Use NestJS built-in exception filters
- Swagger documents error responses
- Return consistent error format:

```json
{
  "statusCode": 404,
  "message": "Category with ID 123 not found",
  "error": "Not Found"
}
```

### Frontend Error Handling

**API Call Errors:**

```typescript
const { data, error, isLoading } = $api.useQuery("get", "/api/categories");

if (error) {
  return <Alert severity="error">{error.message}</Alert>;
}
```

**Component Error Display:**

```typescript
{
  error && <Alert severity="error">Failed to load data: {error.message}</Alert>;
}
```

## Testing Strategy

### Backend Testing

**Unit Tests:**

- Test CategoriesService methods with mocked repositories
- Test DTO transformations
- Test error handling paths

**Integration Tests:**

- Test controller endpoints with test database
- Verify correct HTTP status codes
- Verify response format matches DTOs
- Verify OpenAPI spec is generated correctly

**Test Files:**

- `categories.service.spec.ts`
- `categories.controller.spec.ts`

### Frontend Testing

**Component Tests:**

- Test CategoryCard renders all fields correctly
- Test ProductCard renders all fields and attributes
- Test loading states
- Test error states

**Integration Tests:**

- Test navigation between pages
- Test API integration with mock server

**Test Files:**

- `CategoryCard.test.tsx`
- `ProductCard.test.tsx`
- `categories.test.tsx`
- `category-products.test.tsx`

### Manual Testing Checklist

1. ✓ OpenAPI spec is accessible at /api/docs
2. ✓ Type generation script runs successfully
3. ✓ Categories list loads and displays all categories with all fields
4. ✓ Category cards show all available data
5. ✓ Clicking a category navigates to products page
6. ✓ Products page displays all product fields
7. ✓ Product attributes display correctly
8. ✓ Back button returns to categories list
9. ✓ Error states display when API fails
10. ✓ Loading states display during data fetch
11. ✓ UI is responsive on different screen sizes
12. ✓ TypeScript compilation has no errors

## API Documentation

### GET /api/categories

**Description:** Retrieve all categories with all fields

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "name": "lemon",
    "displayName": "Lemon",
    "productCount": 45,
    "reasoning": "Products that are lemons based on consumer substitutability",
    "confidence": 0.95,
    "schemaId": 3,
    "createdAt": "2025-11-08T10:00:00Z",
    "updatedAt": "2025-11-08T10:00:00Z"
  }
]
```

### GET /api/categories/:id/products

**Description:** Retrieve all products for a category with all fields

**Parameters:**

- `id` (path): Category ID

**Response:** 200 OK

```json
[
  {
    "id": 101,
    "name": "Bio Zitronen",
    "supermarket": "coop",
    "price": 2.95,
    "unit": "500g",
    "unitPrice": 5.9,
    "priceText": "CHF 2.95",
    "hasDiscount": false,
    "discountInfo": null,
    "imageUrl": "https://...",
    "url": "https://...",
    "scrapedFrom": "https://...",
    "categories": ["Früchte", "Bio"],
    "attributes": {
      "organic": true,
      "variety": "eureka"
    },
    "categoryId": 1,
    "categorizationConfidence": 0.95,
    "attributesExtractedAt": "2025-11-08T11:00:00Z",
    "scrapedAt": "2025-11-08T09:00:00Z",
    "createdAt": "2025-11-08T09:30:00Z",
    "updatedAt": "2025-11-08T11:00:00Z"
  }
]
```

**Response:** 404 Not Found

```json
{
  "statusCode": 404,
  "message": "Category with ID 999 not found",
  "error": "Not Found"
}
```

## Implementation Notes

### Backend Implementation Order

1. Install @nestjs/swagger, class-validator, class-transformer
2. Create DTOs with all DB fields and Swagger decorators
3. Create CategoriesService with repository integration
4. Create CategoriesController with Swagger decorators
5. Create CategoriesModule and wire dependencies
6. Configure Swagger in main.ts
7. Add CORS configuration
8. Update AppModule to import CategoriesModule
9. Test OpenAPI spec generation at /api/docs

### Frontend Implementation Order

1. Install openapi-typescript as dev dependency
2. Start backend and generate types with npm script
3. Update API client configuration with generated types
4. Create CategoryCard component
5. Create ProductCard component (with all fields)
6. Create categories list page
7. Create category products page
8. Add routes to routes.ts
9. Add navigation link to header/menu
10. Test type safety and API integration

### Repository Method Usage

**Existing methods to use:**

- `CategoryRepository.getAllCategories()` - returns all fields
- `ProductsRepository.getProductsByCategory(categoryId)` - needs to be updated to return all fields
- `CategoryRepository.getCategory(categoryId)` - for category validation

**Note:** ProductsRepository.getProductsByCategory() currently only selects specific columns. We'll need to modify it to select all columns for prototyping.

### Repository Updates Needed

Update `ProductsRepository.getProductsByCategory()` to return all fields:

```typescript
async getProductsByCategory(categoryId: number) {
  return db
    .select(
      "products",
      { category_id: categoryId },
      { order: { by: "name", direction: "ASC" } }
    )
    .run(this.pool);
}
```

## Performance Considerations

### Backend Optimizations

- Categories query is simple and fast (no joins needed)
- Products query uses indexed category_id column
- No pagination needed for MVP (categories and products per category are manageable)
- OpenAPI spec is generated once at startup

### Frontend Optimizations

- Use React.memo for card components if needed
- Lazy load product images
- openapi-react-query handles caching automatically
- No need for complex state management

### Future Optimizations (Post-MVP)

- Add pagination for large product lists
- Add search/filter functionality
- Implement virtual scrolling for long lists
- Add caching layer (Redis) on backend
- Implement optimistic UI updates

## Security Considerations

### Backend Security

- Input validation on category ID parameter (class-validator)
- SQL injection protection (handled by Zapatos)
- Rate limiting (not needed for MVP, add later)
- Authentication (not needed for MVP, add later)

### Frontend Security

- XSS protection (React handles by default)
- HTTPS in production (not needed for local prototype)
- Type safety prevents many runtime errors

## Deployment Notes

### Development Setup

**Backend:**

```bash
cd backend
yarn add @nestjs/swagger class-validator class-transformer
yarn install
yarn build
yarn start:dev
```

**Frontend:**

```bash
cd frontend
yarn add -D openapi-typescript
yarn install
yarn generate:api  # Generate types from backend
yarn dev
```

**Database:**

```bash
docker-compose up -d
```

### Environment Configuration

**Backend `.env`:**

```
DATABASE_URL=postgresql://pricecomp_user:abc@localhost:5532/pricecomp_db
FRONTEND_URL=http://localhost:5173
```

**Frontend `.env`:**

```
VITE_BACKEND_URL=http://localhost:3000
```

## Design Decisions and Rationale

### Why OpenAPI/Swagger?

- Provides single source of truth for API contract
- Generates interactive API documentation
- Enables type-safe frontend client generation
- Catches API contract mismatches at compile time
- Industry standard for API documentation

### Why Return All DB Fields?

- Prototyping phase needs flexibility to explore all data
- Easier to remove fields later than add them
- Allows frontend to experiment with different visualizations
- No performance concerns for MVP scale
- Can optimize later based on actual usage patterns

### Why openapi-typescript?

- Already configured in the project
- Generates TypeScript types directly from OpenAPI spec
- Works seamlessly with openapi-fetch and openapi-react-query
- Provides full type safety from backend to frontend
- Catches breaking changes at compile time

### Why NestJS Module Structure?

- Follows existing backend architecture
- Provides dependency injection for repositories
- Enables easy testing with mocked dependencies
- Scales well if we add more features later

### Why Material-UI?

- Already configured in the frontend
- Provides consistent, professional components
- Responsive by default
- Reduces custom CSS needed

### Why No Pagination?

- MVP focused on quick prototyping
- Category count is manageable (< 100 expected)
- Products per category are manageable (< 500 expected)
- Can add pagination later if needed
