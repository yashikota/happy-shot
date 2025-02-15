package main

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type MinioClient struct {
	client *minio.Client
}

var (
	minioOnce   sync.Once
	minioClient *MinioClient
)

func NewMinioClient(endpoint, accessKey, secretKey string) *MinioClient {
	log.Printf("Initializing MinIO client with endpoint: %s", endpoint)
	minioOnce.Do(func() {
		client, err := minio.New(endpoint, &minio.Options{
			Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
			Secure: true,
		})
		if err != nil {
			log.Fatalf("Failed to create MinIO client: %v", err)
		}
		minioClient = &MinioClient{client: client}
	})
	return minioClient
}

func (mc *MinioClient) UploadImage(bucket, objectName string, file io.Reader, fileSize int64) error {
	log.Printf("Uploading image to bucket: %s, object name: %s", bucket, objectName)
	exists, err := mc.client.BucketExists(context.Background(), bucket)
	if err != nil {
		return err
	}
	if !exists {
		if err := mc.client.MakeBucket(context.Background(), bucket, minio.MakeBucketOptions{}); err != nil {
			return err
		}
	}
	_, err = mc.client.PutObject(context.Background(), bucket, objectName, file, fileSize, minio.PutObjectOptions{ContentType: "image/jpeg"})
	return err
}

func (mc *MinioClient) GetPresignedURLs(bucket string) ([]string, error) {
	log.Printf("Fetching presigned URLs for bucket: %s", bucket)
	var urls []string
	objects := mc.client.ListObjects(context.Background(), bucket, minio.ListObjectsOptions{})

	for object := range objects {
		url, err := mc.client.PresignedGetObject(context.Background(), bucket, object.Key, 24*time.Hour, nil)
		if err != nil {
			return nil, err
		}
		urls = append(urls, url.String())
	}
	return urls, nil
}

func (mc *MinioClient) DownloadAllImages(bucket string) (*bytes.Buffer, error) {
	log.Printf("Downloading all images from bucket: %s", bucket)
	exists, err := mc.client.BucketExists(context.Background(), bucket)
	if err != nil || !exists {
		return nil, fmt.Errorf("bucket not found")
	}

	buffer := new(bytes.Buffer)
	zipWriter := zip.NewWriter(buffer)
	defer zipWriter.Close()

	objects := mc.client.ListObjects(context.Background(), bucket, minio.ListObjectsOptions{})
	for object := range objects {
		file, err := mc.client.GetObject(context.Background(), bucket, object.Key, minio.GetObjectOptions{})
		if err != nil {
			return nil, err
		}
		defer file.Close()

		zipFile, err := zipWriter.Create(object.Key)
		if err != nil {
			return nil, err
		}

		if _, err := io.Copy(zipFile, file); err != nil {
			return nil, err
		}
	}

	if err := zipWriter.Close(); err != nil {
		return nil, err
	}

	return buffer, nil
}

func main() {
	r := gin.Default()

	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "*")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	})

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	endpoint := os.Getenv("MINIO_ENDPOINT")
	accessKey := os.Getenv("MINIO_ACCESS_KEY")
	secretKey := os.Getenv("MINIO_SECRET_KEY")

	log.Println("Starting server on port 5000...")
	minioClient := NewMinioClient(endpoint, accessKey, secretKey)

	r.POST("/upload", func(c *gin.Context) {
		bucket := c.Query("bucket")
		file, header, err := c.Request.FormFile("file")
		if err != nil {
			log.Printf("Upload error: %v", err)
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		defer file.Close()
		err = minioClient.UploadImage(bucket, header.Filename, file, header.Size)
		if err != nil {
			log.Printf("Upload failed: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "Upload successful"})
	})

	r.GET("/images", func(c *gin.Context) {
		bucket := c.Query("bucket")
		urls, err := minioClient.GetPresignedURLs(bucket)
		if err != nil {
			log.Printf("Error fetching presigned URLs: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.Writer.Header().Set("Content-Type", "application/json")
		encoder := json.NewEncoder(c.Writer)
		encoder.SetEscapeHTML(false)
		encoder.Encode(gin.H{"images": urls})
	})

	r.GET("/download", func(c *gin.Context) {
		bucket := c.Query("bucket")
		zipBuffer, err := minioClient.DownloadAllImages(bucket)
		if err != nil {
			log.Printf("Download error: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.Header("Content-Disposition", "attachment; filename=images.zip")
		c.Data(http.StatusOK, "application/zip", zipBuffer.Bytes())
	})

	r.Run(":5000")
}
