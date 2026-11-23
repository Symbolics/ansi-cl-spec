;;; Print all external symbols of COMMON-LISP, lowercased, sorted, one per line.
;;; Usage: sbcl --script tools/lisp/cl-symbols.lisp > tools/data/cl-symbols.txt
(let ((names '()))
  (do-external-symbols (s :common-lisp)
    (push (string-downcase (symbol-name s)) names))
  (dolist (n (sort names #'string<))
    (write-line n)))
