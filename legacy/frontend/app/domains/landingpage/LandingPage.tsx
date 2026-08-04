import React, { useState } from "react";
import { ArrowBack, OpenInNew } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  CardMedia,
  Chip,
  CircularProgress,
  Container,
  IconButton,
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
                  sm: "repeat(3, 1fr)",
                  md: "repeat(4, 1fr)",
                },
                gap: 3,
              }}
            >
              {products.map((product: ProductDto) => (
                <Card key={product.id}>
                  {product.imageUrl && (
                    <Box sx={{ position: "relative" }}>
                      <CardMedia
                        component="img"
                        height="200"
                        image={product.imageUrl}
                        alt={product.name}
                        sx={{ objectFit: "contain", bgcolor: "grey.100" }}
                      />
                      {product.productUrl && (
                        <IconButton
                          component="a"
                          href={product.productUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          sx={{
                            position: "absolute",
                            top: 8,
                            right: 8,
                            bgcolor: "background.paper",
                            "&:hover": {
                              bgcolor: "primary.main",
                              color: "white",
                            },
                          }}
                          size="small"
                        >
                          <OpenInNew fontSize="small" />
                        </IconButton>
                      )}
                    </Box>
                  )}
                  <CardContent>
                    <Typography variant="h6" component="h3" gutterBottom>
                      {product.name}
                    </Typography>

                    <Box
                      sx={{
                        mb: 2,
                        display: "flex",
                        gap: 0.5,
                        flexWrap: "wrap",
                      }}
                    >
                      <Chip
                        label={product.supermarket}
                        size="small"
                        color="primary"
                      />
                      {product.isDiscounted && (
                        <Chip label="Discounted" size="small" color="error" />
                      )}
                    </Box>

                    <Typography
                      variant="body2"
                      color="text.secondary"
                      gutterBottom
                    >
                      <strong>Price:</strong>{" "}
                      {product.priceText ||
                        (product.price
                          ? `${product.price} ${product.currency || "CHF"}`
                          : "N/A")}
                    </Typography>

                    {product.discountInfo && (
                      <Typography variant="body2" color="error" gutterBottom>
                        <strong>Discount:</strong> {product.discountInfo}
                      </Typography>
                    )}

                    <Typography
                      variant="body2"
                      color="text.secondary"
                      gutterBottom
                    >
                      <strong>Unit:</strong> {product.unit || "N/A"}
                    </Typography>

                    {product.unitPrice && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        <strong>Unit Price:</strong> {product.unitPrice}
                      </Typography>
                    )}

                    {(product.originalQuantity || product.originalUnit) && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        <strong>Original:</strong> {product.originalQuantity}{" "}
                        {product.originalUnit}
                      </Typography>
                    )}

                    {(product.normalizedQuantity || product.normalizedUnit) && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        <strong>Normalized:</strong>{" "}
                        {product.normalizedQuantity} {product.normalizedUnit}
                        {product.normalizedPrice &&
                          ` (${product.normalizedPrice} ${product.currency || "CHF"}/${product.normalizedUnit})`}
                      </Typography>
                    )}

                    {product.categoryId && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        <strong>Category ID:</strong> {product.categoryId}
                        {product.categorizationConfidence &&
                          ` (${(product.categorizationConfidence * 100).toFixed(0)}%)`}
                      </Typography>
                    )}

                    {product.attributes &&
                      Object.keys(product.attributes).length > 0 && (
                        <Box sx={{ mt: 1 }}>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            gutterBottom
                          >
                            <strong>Attributes:</strong>
                          </Typography>
                          <Box
                            sx={{
                              display: "flex",
                              gap: 0.5,
                              flexWrap: "wrap",
                            }}
                          >
                            {Object.entries(product.attributes).map(
                              ([key, value]) => (
                                <Chip
                                  key={key}
                                  label={`${key}: ${JSON.stringify(value)}`}
                                  size="small"
                                  variant="outlined"
                                />
                              )
                            )}
                          </Box>
                        </Box>
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
                      {category.productCount
                        ? `${category.productCount} products`
                        : "No products"}
                    </Typography>
                    {category.confidence && (
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
