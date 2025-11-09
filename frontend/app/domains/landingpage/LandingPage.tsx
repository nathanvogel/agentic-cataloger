import React, { useState } from "react";
import { ArrowBack } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Typography,
} from "@mui/material";
import { $api } from "../../schema/api";
import type { components } from "../../schema/backend-schema";

type CategoryDto = components["schemas"]["CategoryResponseDto"];
type ProductDto = components["schemas"]["ProductResponseDto"];

const LandingPage: React.FC = () => {
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(
    null
  );

  // Fetch categories
  const {
    data: categories,
    isLoading: categoriesLoading,
    error: categoriesError,
  } = $api.useQuery("get", "/api/categories");

  // Fetch products for selected category
  const {
    data: products,
    isLoading: productsLoading,
    error: productsError,
  } = $api.useQuery(
    "get",
    "/api/categories/{id}/products",
    {
      params: {
        path: { id: selectedCategoryId ?? 0 },
      },
    },
    {
      enabled: selectedCategoryId !== null,
    }
  );

  const selectedCategory = categories?.find(
    (cat) => cat.id === selectedCategoryId
  );

  const handleCategoryClick = (categoryId: number) => {
    setSelectedCategoryId(categoryId);
  };

  const handleBackToCategories = () => {
    setSelectedCategoryId(null);
  };

  // Show products view if a category is selected
  if (selectedCategoryId !== null) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={handleBackToCategories}
            sx={{ mb: 3 }}
          >
            Back to Categories
          </Button>

          <Typography variant="h4" component="h1" gutterBottom>
            {selectedCategory?.displayName || "Category"}
          </Typography>

          {productsLoading && (
            <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          )}

          {productsError && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Failed to load products. Please try again.
            </Alert>
          )}

          {products && products.length === 0 && (
            <Alert severity="info">No products found in this category.</Alert>
          )}

          {products && products.length > 0 && (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2, 1fr)",
                  md: "repeat(3, 1fr)",
                },
                gap: 3,
              }}
            >
              {products.map((product: ProductDto) => (
                <Card key={product.id}>
                  <CardContent>
                    <Typography variant="h6" component="h3" gutterBottom>
                      {product.name}
                    </Typography>
                    <Chip
                      label={product.supermarket}
                      size="small"
                      color="primary"
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      Price:{" "}
                      {product.price && typeof product.price === "number"
                        ? `CHF ${product.price}`
                        : "N/A"}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Unit:{" "}
                      {product.unit && typeof product.unit === "string"
                        ? product.unit
                        : "N/A"}
                    </Typography>
                    {product.categorizationConfidence &&
                      typeof product.categorizationConfidence === "number" && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mt: 1 }}
                        >
                          Confidence:{" "}
                          {(product.categorizationConfidence * 100).toFixed(0)}%
                        </Typography>
                      )}
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </Box>
      </Container>
    );
  }

  // Show categories view
  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          Product Categories
        </Typography>
        <Typography
          variant="body1"
          color="text.secondary"
          align="center"
          sx={{ mb: 4 }}
        >
          Browse our product categories to explore available items
        </Typography>

        {categoriesLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress />
          </Box>
        )}

        {categoriesError && (
          <Alert severity="error">
            Failed to load categories. Please try again.
          </Alert>
        )}

        {categories && categories.length === 0 && (
          <Alert severity="info">No categories available.</Alert>
        )}

        {categories && categories.length > 0 && (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, 1fr)",
                md: "repeat(3, 1fr)",
              },
              gap: 3,
            }}
          >
            {categories.map((category: CategoryDto) => (
              <Card key={category.id}>
                <CardActionArea
                  onClick={() => handleCategoryClick(category.id)}
                >
                  <CardContent>
                    <Typography variant="h5" component="h2" gutterBottom>
                      {category.displayName}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {category.productCount &&
                      typeof category.productCount === "number"
                        ? `${category.productCount} products`
                        : "No products"}
                    </Typography>
                    {category.confidence &&
                      typeof category.confidence === "number" && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mt: 1 }}
                        >
                          Confidence: {(category.confidence * 100).toFixed(0)}%
                        </Typography>
                      )}
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default LandingPage;
