;;; Evaluate the steps of ONE dictionary entry in this fresh image.
;;; Usage: sbcl --script run-example.lisp INPUT-FILE
;;; INPUT-FILE: a sequence of Lisp strings, one per step (each string may hold
;;; several forms; all are evaluated, the values of the last are reported).
;;; Output (stdout), line oriented; \ and newline are escaped as \\ and \n:
;;;   STEP <i>          start of step i (0-based)
;;;   OUT <text>        one line of text written to *standard-output*
;;;   VAL <text>        prin1 of one returned value
;;;   NOVALUES          form returned no values
;;;   ERR <type> <msg>  evaluation signalled an error
;;;   TIMEOUT           step exceeded its time budget
;;;   END <i>           step finished
(defun esc (s)
  (with-output-to-string (o)
    (loop for c across s
          do (case c
               (#\\ (write-string "\\\\" o))
               (#\Newline (write-string "\\n" o))
               (#\Return (write-string "\\r" o))
               (t (write-char c o))))))

(defvar *real-out* *standard-output*)
(defun emit (tag &optional (text ""))
  (format *real-out* "~A ~A~%" tag (esc text))
  (finish-output *real-out*))

(defun eval-forms (string)
  (let ((vals nil))
    (with-input-from-string (in string)
      (loop for form = (read in nil in)
            until (eq form in)
            do (let ((new (multiple-value-list (eval form))))
                 (setf vals new)
                 ;; REPL history variables
                 (shiftf +++ ++ + form)
                 (shiftf *** ** * (car new))
                 (shiftf /// // / new))))
    vals))

(defun run-step (i string)
  (emit "STEP" (princ-to-string i))
  (let ((out (make-string-output-stream))
        (vals nil) (ok nil))
    (block step
      (handler-case
          (sb-ext:with-timeout 5
            (let ((*standard-output* out)
                  (*terminal-io* (make-two-way-stream (make-string-input-stream "") out))
                  (*error-output* (make-broadcast-stream))
                  (*query-io* (make-two-way-stream (make-string-input-stream "")
                                                   (make-broadcast-stream)))
                  (*print-readably* nil))
              (setf vals (eval-forms string) ok t)))
        (sb-ext:timeout () (emit "TIMEOUT") (return-from step))
        (serious-condition (c)
          (let ((msg (handler-case (princ-to-string c)
                       (serious-condition () "<unprintable condition>"))))
            (setf ok :error)
            (let ((text (get-output-stream-string out)))
              (dolist (l (split-lines text)) (emit "OUT" l)))
            (emit "ERR" (format nil "~A ~A" (type-of c) msg))
            (return-from step))))
      (dolist (l (split-lines (get-output-stream-string out))) (emit "OUT" l))
      (when ok
        (if (null vals)
            (emit "NOVALUES")
            (dolist (v vals)
              (emit "VAL"
                    (handler-case
                        (let ((*print-readably* nil)) (prin1-to-string v))
                      (serious-condition () "#<unprintable>")))))))
    (emit "END" (princ-to-string i))))

(defun split-lines (text)
  (if (zerop (length text))
      nil
      (let ((lines nil) (start 0))
        (loop for p = (position #\Newline text :start start)
              do (push (subseq text start (or p (length text))) lines)
                 (if p (setf start (1+ p)) (return)))
        ;; a trailing newline does not start a new (empty) line
        (when (and (string= (car lines) "")) (pop lines))
        (nreverse lines))))

(let* ((file (car (last sb-ext:*posix-argv*)))
       (steps (with-open-file (in file :external-format :utf-8)
                (let ((*read-eval* nil))
                  (loop for s = (read in nil in) until (eq s in) collect s)))))
  (with-standard-io-syntax
    (setf *read-eval* t)
    (let ((*print-readably* nil))
      (loop for s in steps for i from 0 do (run-step i s)))))
