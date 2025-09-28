import { useCallback, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, Camera, FileText, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Alert, AlertDescription } from '../ui/alert';
import { Progress } from '../ui/progress';
import { receiptsAPI } from '../../services/api';
import { Receipt } from '../../types';

interface ReceiptUploadProps {
  onUploadSuccess?: (receipt: Receipt) => void;
}

export function ReceiptUpload({ onUploadSuccess }: ReceiptUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: receiptsAPI.upload,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['receipts'] });
      setSelectedFile(null);
      onUploadSuccess?.(data.receipt);
    },
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      }
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      }
    }
  };

  const validateFile = (file: File): boolean => {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!validTypes.includes(file.type)) {
      alert('Please select a valid image file (JPEG, PNG) or PDF');
      return false;
    }

    if (file.size > maxSize) {
      alert('File size must be less than 10MB');
      return false;
    }

    return true;
  };

  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  const handleCameraCapture = () => {
    // For mobile camera capture
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment'; // Use rear camera
    input.onchange = (e) => {
      const target = e.target as HTMLInputElement;
      if (target.files && target.files[0]) {
        const file = target.files[0];
        if (validateFile(file)) {
          setSelectedFile(file);
        }
      }
    };
    input.click();
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Upload Receipt
        </CardTitle>
        <CardDescription>
          Upload a photo or PDF of your receipt to start the splitting process
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {uploadMutation.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {uploadMutation.error instanceof Error 
                ? uploadMutation.error.message 
                : 'Upload failed. Please try again.'}
            </AlertDescription>
          </Alert>
        )}

        {!selectedFile ? (
          <>
            {/* Drag and Drop Area */}
            <div
              className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive 
                  ? 'border-primary bg-primary/5' 
                  : 'border-muted-foreground/25 hover:border-muted-foreground/50'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <p className="mb-2">
                Drag and drop your receipt here, or
              </p>
              <Button variant="outline" onClick={() => document.getElementById('file-input')?.click()}>
                Browse Files
              </Button>
              <input
                id="file-input"
                type="file"
                accept="image/*,.pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
              <p className="text-sm text-muted-foreground mt-2">
                Supports JPEG, PNG, and PDF files up to 10MB
              </p>
            </div>

            {/* Camera Capture Button (Mobile) */}
            <div className="flex justify-center">
              <Button variant="outline" onClick={handleCameraCapture} className="flex items-center gap-2">
                <Camera className="h-4 w-4" />
                Take Photo
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* Selected File Preview */}
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="h-8 w-8 text-primary" />
                  <div>
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setSelectedFile(null)}
                  disabled={uploadMutation.isPending}
                >
                  Remove
                </Button>
              </div>

              {/* File Preview (for images) */}
              {selectedFile.type.startsWith('image/') && (
                <div className="mt-4">
                  <img
                    src={URL.createObjectURL(selectedFile)}
                    alt="Receipt preview"
                    className="max-w-full h-32 object-contain rounded border"
                  />
                </div>
              )}
            </div>

            {/* Upload Progress */}
            {uploadMutation.isPending && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Uploading and processing...</span>
                  <span>Please wait</span>
                </div>
                <Progress value={undefined} className="w-full" />
              </div>
            )}

            {/* Upload Button */}
            <Button 
              onClick={handleUpload} 
              className="w-full" 
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? 'Processing...' : 'Upload Receipt'}
            </Button>
          </>
        )}

        {/* Success Message */}
        {uploadMutation.isSuccess && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Receipt uploaded successfully! OCR processing has started.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}