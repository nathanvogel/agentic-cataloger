# Requirements Document

## Introduction

This feature provides a simple web interface for exploring product categories and viewing all products within each category. The goal is to prototype UX patterns for category browsing and product exploration, enabling quick validation of the categorization system's output. This is a minimal viable prototype focused on data visualization rather than production-ready features.

## Glossary

- **Category Browser**: A web interface that displays all categories and allows navigation to view products within each category
- **Backend API**: RESTful endpoints in the NestJS backend that serve category and product data
- **Frontend UI**: React-based interface that consumes the backend API and displays categories and products

## Requirements

### Requirement 1

**User Story:** As a developer, I want a backend API endpoint that returns all categories with their product counts, so that the frontend can display a list of available categories.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/categories`, THE Backend API SHALL return all categories from the categories table
2. THE Backend API SHALL include the following fields for each category: id, name, display_name, product_count, created_at
3. THE Backend API SHALL order categories by product_count in descending order
4. THE Backend API SHALL return data in JSON format
5. WHEN no categories exist, THE Backend API SHALL return an empty array with HTTP 200 status

### Requirement 2

**User Story:** As a developer, I want a backend API endpoint that returns all products for a specific category, so that the frontend can display products when a category is selected.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/categories/:id/products`, THE Backend API SHALL return all products assigned to that category
2. THE Backend API SHALL include the following fields for each product: id, name, supermarket, price, unit, image_url, attributes, categorization_confidence
3. THE Backend API SHALL order products by name alphabetically
4. WHEN the category ID does not exist, THE Backend API SHALL return HTTP 404 with an error message
5. WHEN a category has no products, THE Backend API SHALL return an empty array with HTTP 200 status

### Requirement 3

**User Story:** As a user, I want to see a list of all categories on the main page, so that I can browse available product categories.

#### Acceptance Criteria

1. WHEN the category browser page loads, THE Frontend UI SHALL fetch and display all categories from the backend API
2. THE Frontend UI SHALL display each category with its display_name and product_count
3. THE Frontend UI SHALL make categories clickable to navigate to the product list
4. WHEN categories are loading, THE Frontend UI SHALL display a loading indicator
5. WHEN the API request fails, THE Frontend UI SHALL display an error message

### Requirement 4

**User Story:** As a user, I want to click on a category and see all products in that category, so that I can explore what products have been categorized together.

#### Acceptance Criteria

1. WHEN a user clicks on a category, THE Frontend UI SHALL navigate to a product list view for that category
2. THE Frontend UI SHALL display the category display_name as a page header
3. THE Frontend UI SHALL fetch and display all products for the selected category
4. THE Frontend UI SHALL display each product with: name, supermarket, price, unit, and image (if available)
5. THE Frontend UI SHALL provide a way to navigate back to the category list

### Requirement 5

**User Story:** As a user, I want to see product attributes in the product list, so that I can understand what information has been extracted for each product.

#### Acceptance Criteria

1. WHEN displaying a product, THE Frontend UI SHALL show the product's attributes from the JSONB column
2. THE Frontend UI SHALL format attributes in a readable way (e.g., key-value pairs or badges)
3. WHEN a product has no attributes, THE Frontend UI SHALL display "No attributes" or hide the attributes section
4. THE Frontend UI SHALL display the categorization_confidence score if available
5. THE Frontend UI SHALL use visual styling to distinguish between different attribute types

### Requirement 6

**User Story:** As a developer, I want the backend API to handle CORS properly, so that the frontend can make requests during development.

#### Acceptance Criteria

1. THE Backend API SHALL enable CORS for the frontend development URL (http://localhost on any port)
2. THE Backend API SHALL accept GET requests from the frontend origin
3. THE Backend API SHALL include appropriate CORS headers in responses
4. WHEN running in development mode, THE Backend API SHALL allow all origins for easier testing
5. THE Backend API SHALL log CORS-related errors for debugging

### Requirement 7

**User Story:** As a user, I want the UI to be responsive and visually clean, so that I can easily browse categories and products on different screen sizes.

#### Acceptance Criteria

1. THE Frontend UI SHALL use a responsive layout that works on desktop and tablet screens
2. THE Frontend UI SHALL use the existing Material-UI theme from the frontend application
3. THE Frontend UI SHALL display categories in a grid or card layout
4. THE Frontend UI SHALL display products in a list or grid layout with clear visual separation
5. THE Frontend UI SHALL use appropriate spacing, typography, and colors for readability

### Requirement 8

**User Story:** As a developer, I want basic error handling in both frontend and backend, so that issues are visible during prototyping.

#### Acceptance Criteria

1. WHEN a backend API error occurs, THE Backend API SHALL return appropriate HTTP status codes (404, 500, etc.)
2. WHEN a backend API error occurs, THE Backend API SHALL return a JSON error response with a message field
3. WHEN a frontend API request fails, THE Frontend UI SHALL display the error message to the user
4. THE Frontend UI SHALL log errors to the browser console for debugging
5. THE Backend API SHALL log errors to the console with sufficient context for debugging
