# Customer-Facing API Documentation

## Overview
This document describes the REST API endpoints for customer-facing operations in the vehicle rental system. These endpoints are designed to be consumed by a React frontend application.

## Base URL
```
http://your-domain.com/vehicle-rental/api/customer/
```

## Authentication
- Most endpoints require authentication via Django REST Framework's SessionAuthentication or TokenAuthentication
- Registration endpoint is public (no authentication required)
- Vehicle browsing endpoints are public

---

## Quick Reference - All Endpoints

### Authentication
- `POST /vehicle-rental/api/customer/login/` - Customer login (returns token + profile)
- `POST /api-token-auth/` - Generic token authentication

### Customer Management
- `POST /vehicle-rental/api/customer/register/` - Register new customer
- `GET /vehicle-rental/api/customer/register/me/` - Get customer profile (auth required)
- `PATCH /vehicle-rental/api/customer/register/update_profile/` - Update profile (auth required)

### Vehicle Browsing
- `GET /vehicle-rental/api/customer/vehicles/` - List available vehicles
- `GET /vehicle-rental/api/customer/vehicles/{id}/` - Get vehicle details
- `GET /vehicle-rental/api/customer/vehicles/{id}/availability/` - Check vehicle availability

### Rentals
- `GET /vehicle-rental/api/customer/rentals/` - List customer rentals (auth required)
- `GET /vehicle-rental/api/customer/rentals/active/` - Get active rentals (auth required)
- `GET /vehicle-rental/api/customer/rentals/history/` - Get rental history (auth required)
- `POST /vehicle-rental/api/customer/rentals/{id}/cancel/` - Cancel rental (auth required)

### Evaluations
- `GET /vehicle-rental/api/customer/evaluations/` - List customer evaluations (auth required)
- `POST /vehicle-rental/api/customer/evaluations/` - Create evaluation (auth required)

---

## Endpoints

### 1. Customer Registration

#### Register New Customer
**POST** `/register/`

Register a new customer account with automatic user creation and "customer" group assignment.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone_number": "+351987654321",
  "address_line_1": "Rua Principal 123",
  "address_line_2": "Apt 4B",
  "city": "Lisboa",
  "postal_code": "1000-001",
  "country": "Portugal",
  "id_number": "PT123456789",
  "driving_license_number": "DL987654321",
  "license_expiry_date": "2026-12-31",
  "password": "SecurePass123",
  "password_confirm": "SecurePass123"
}
```

**Response (201 Created):**
```json
{
  "message": "Customer registered successfully",
  "customer": {
    "id": 1,
    "username": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+351987654321",
    "city": "Lisboa",
    "created_at": "2025-11-17T09:00:00Z"
  }
}
```

**Validations:**
- Passwords must match
- Email must be unique
- Driving license must not be expired
- Password must be at least 8 characters

---

#### Get Customer Profile
**GET** `/register/me/`

Get the authenticated customer's profile information.

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone_number": "+351987654321",
  "address_line_1": "Rua Principal 123",
  "city": "Lisboa",
  "rental_count": 5,
  "active_rentals": 1,
  "is_blacklisted": false,
  "created_at": "2025-11-17T09:00:00Z"
}
```

---

#### Update Customer Profile
**PATCH** `/register/update_profile/`

Update the authenticated customer's profile information.

**Authentication:** Required

**Request Body** (partial update supported):
```json
{
  "phone_number": "+351999888777",
  "address_line_1": "New Address 456"
}
```

**Response (200 OK):**
```json
{
  "message": "Profile updated successfully",
  "customer": {
    ...updated customer data...
  }
}
```

---

### 2. Vehicle Availability

#### List Available Vehicles
**GET** `/vehicles/`

Browse all available vehicles. Optionally filter by date range to check availability.

**Authentication:** Not required (public)

**Query Parameters:**
- `start_date` (optional): ISO 8601 date (e.g., "2025-12-01T10:00:00")
- `end_date` (optional): ISO 8601 date

**Example Request:**
```
GET /vehicles/?start_date=2025-12-01T10:00:00&end_date=2025-12-10T10:00:00
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "brand_name": "Toyota",
    "model": "Corolla",
    "year": 2023,
    "registration_number": "AB-12-CD",
    "fuel_type": "hybrid",
    "gearbox_type": "automatic",
    "daily_rate": "45.00",
    "number_of_seats": 5,
    "is_available": true,
    "photo": "/media/vehicle_photos/1/main.jpg",
    "photos_count": 5
  }
]
```

---

#### Get Vehicle Detail
**GET** `/vehicles/{id}/`

Get detailed information about a specific vehicle.

**Authentication:** Not required (public)

**Response (200 OK):**
```json
{
  "id": 1,
  "brand_name": "Toyota",
  "model": "Corolla",
  "year": 2023,
  "description": "Comfortable sedan with excellent fuel economy",
  "registration_number": "AB-12-CD",
  "color": "Silver",
  "fuel_type": "hybrid",
  "gearbox_type": "automatic",
  "air_conditioning": true,
  "panoramic_roof": false,
  "number_of_seats": 5,
  "mileage": 15000,
  "daily_rate": "45.00",
  "is_available": true,
  "primary_photo": {
    "id": 1,
    "image": "/media/vehicle_photos/1/main.jpg",
    "title": "Front view"
  },
  "additional_photos": [
    {
      "id": 2,
      "image": "/media/vehicle_photos/1/interior.jpg",
      "title": "Interior"
    }
  ]
}
```

---

#### Check Vehicle Availability
**GET** `/vehicles/{id}/availability/`

Check if a specific vehicle is available for a given date range.

**Authentication:** Not required (public)

**Query Parameters:**
- `start_date` (required): ISO 8601 date
- `end_date` (required): ISO 8601 date

**Example Request:**
```
GET /vehicles/1/availability/?start_date=2025-12-01T10:00:00&end_date=2025-12-10T10:00:00
```

**Response (200 OK):**
```json
{
  "vehicle_id": 1,
  "registration_number": "AB-12-CD",
  "is_available": true,
  "start_date": "2025-12-01T10:00:00",
  "end_date": "2025-12-10T10:00:00"
}
```

---

### 3. Customer Rentals

#### List Customer Rentals
**GET** `/rentals/`

Get all rentals for the authenticated customer.

**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "vehicle_info": {
      "id": 1,
      "brand": "Toyota",
      "model": "Corolla",
      "year": 2023,
      "registration_number": "AB-12-CD",
      "photo": "/media/vehicle_photos/1/main.jpg"
    },
    "start_date": "2025-11-20T10:00:00Z",
    "end_date": "2025-11-25T10:00:00Z",
    "days_duration": 5,
    "total_amount": "225.00",
    "status": "active",
    "status_display": "Ativo",
    "notes": "",
    "evaluation": null,
    "created_at": "2025-11-15T09:00:00Z"
  }
]
```

---

#### Get Active Rentals
**GET** `/rentals/active/`

Get only active rentals (pending, confirmed, or active status).

**Authentication:** Required

**Response:** Same format as List Customer Rentals

---

#### Get Rental History
**GET** `/rentals/history/`

Get completed or cancelled rentals.

**Authentication:** Required

**Response:** Same format as List Customer Rentals

---

#### Cancel Rental
**POST** `/rentals/{id}/cancel/`

Cancel a pending or confirmed rental.

**Authentication:** Required

**Response (200 OK):**
```json
{
  "message": "Rental cancelled successfully",
  "rental": {
    ...updated rental data with status='cancelled'...
  }
}
```

**Error Responses:**
- `400 Bad Request`: If rental cannot be cancelled (already active or completed)

---

### 4. Rental Evaluations

#### List Customer Evaluations
**GET** `/evaluations/`

Get all evaluations created by the authenticated customer.

**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "rental": 1,
    "overall_rating": 5,
    "vehicle_condition_rating": 5,
    "service_quality_rating": 4,
    "value_for_money_rating": 5,
    "comments": "Excellent service and great car!",
    "had_issues": false,
    "created_at": "2025-11-26T10:00:00Z"
  }
]
```

---

#### Create Rental Evaluation
**POST** `/evaluations/`

Create an evaluation for a completed rental.

**Authentication:** Required

**Request Body:**
```json
{
  "rental": 1,
  "overall_rating": 5,
  "vehicle_condition_rating": 5,
  "service_quality_rating": 4,
  "value_for_money_rating": 5,
  "comments": "Excellent service and great car!",
  "had_issues": false,
  "issue_description": "",
  "would_recommend": true
}
```

**Response (201 Created):**
```json
{
  "message": "Evaluation created successfully",
  "evaluation": {
    ...created evaluation data...
  }
}
```

**Validations:**
- Rental must belong to the authenticated customer
- Rental must have status 'completed'
- Rental can only be evaluated once
- Ratings must be between 1 and 5
- If `had_issues` is true, `issue_description` must be provided

---

## Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data or validation error
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Error Response Format

```json
{
  "error": "Error message description",
  "field_name": ["Specific field error message"]
}
```

---

## Authentication Methods

### 1. Customer Login API (Recommended)
**POST** `/vehicle-rental/api/customer/login/`

Custom login endpoint that returns token and customer profile information.

**Request Body:**
```json
{
  "email": "customer@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "token": "abc123def456...",
  "user": {
    "id": 1,
    "username": "customer@example.com",
    "email": "customer@example.com",
    "is_customer": true
  },
  "customer": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "customer@example.com",
    "phone_number": "+351987654321",
    "city": "Lisboa",
    "rental_count": 5,
    "active_rentals": 1,
    "is_blacklisted": false
  },
  "message": "Login successful"
}
```

**Error Responses:**
- `400 Bad Request`: Missing email or password
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Not a customer account or account suspended

**Usage in React:**
```javascript
const loginCustomer = async (email, password) => {
  const response = await fetch('http://84.247.171.243:8090/vehicle-rental/api/customer/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }
  
  const data = await response.json();
  // Store token securely (e.g., localStorage or secure cookie)
  localStorage.setItem('authToken', data.token);
  localStorage.setItem('customer', JSON.stringify(data.customer));
  
  return data;
};
```

### 2. Generic Token Authentication (Alternative)
**POST** `/api-token-auth/` or `/vehicle-rental/api-token-auth/`

Standard DRF token authentication endpoint.

**Request Body:**
```json
{
  "username": "customer@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "token": "abc123def456..."
}
```

**Note:** This endpoint returns only the token. Use the customer login endpoint above to get customer profile data along with the token.

### Using the Token in API Requests

Include the token in the Authorization header:

```javascript
const getCustomerProfile = async () => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    'http://84.247.171.243:8090/vehicle-rental/api/customer/register/me/',
    {
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );
  
  return await response.json();
};
```

---

## CORS Configuration

The API is configured to allow requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)
- `http://localhost:4200` (Angular default)

Additional origins can be configured in `config/settings.py`

---

## Rate Limiting

Currently no rate limiting is implemented. Consider adding rate limiting for production use.

---

## Notes for Frontend Development

1. **Date Format**: Use ISO 8601 format for all dates
2. **File Uploads**: Vehicle photos are returned as URLs
3. **Authentication**: Store session/token securely
4. **Error Handling**: Always check response status and handle errors appropriately
5. **Validation**: Perform client-side validation before API calls to improve UX

---

## Example React Integration

```javascript
// Login customer
const loginCustomer = async (email, password) => {
  const response = await fetch('http://84.247.171.243:8090/vehicle-rental/api/customer/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  
  if (!response.ok) {
    throw new Error('Login failed');
  }
  
  const data = await response.json();
  // Store token and customer data
  localStorage.setItem('authToken', data.token);
  localStorage.setItem('customer', JSON.stringify(data.customer));
  return data;
};

// Register new customer
const registerCustomer = async (customerData) => {
  const response = await fetch('http://84.247.171.243:8090/vehicle-rental/api/customer/register/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(customerData),
  });
  return await response.json();
};

// Get available vehicles
const getAvailableVehicles = async (startDate, endDate) => {
  const params = new URLSearchParams({
    start_date: startDate.toISOString(),
    end_date: endDate.toISOString(),
  });
  const response = await fetch(
    `http://84.247.171.243:8090/vehicle-rental/api/customer/vehicles/?${params}`
  );
  return await response.json();
};

// Get customer profile (with authentication)
const getCustomerProfile = async () => {
  const token = localStorage.getItem('authToken');
  const response = await fetch(
    'http://84.247.171.243:8090/vehicle-rental/api/customer/register/me/',
    {
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );
  return await response.json();
};

// Logout customer
const logoutCustomer = () => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('customer');
};
```

---

## Testing

A test script is provided at `/test_customer_api.py` for testing all endpoints.

Run with:
```bash
source venv_sga/bin/activate
python test_customer_api.py
```

---

## Swagger Documentation

Interactive API documentation available at:
```
http://localhost:8090/swagger/
```

---

## Support

For issues or questions, please contact the development team.
