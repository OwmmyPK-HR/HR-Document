document.addEventListener('DOMContentLoaded', function() {

    // --- PDF Popup Modal Logic ---
    const pdfModal = document.getElementById('pdfViewerModal');
    const pdfFrame = document.getElementById('pdfFrame');
    const closeModalBtn = document.querySelector('.close-modal-btn');

    document.querySelectorAll('.view-pdf-btn').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const pdfUrl = this.dataset.pdfUrl;
            if (pdfFrame && pdfUrl) {
                pdfFrame.src = pdfUrl;
                if (pdfModal) pdfModal.style.display = 'block';
            }
        });
    });

    if (closeModalBtn) {
        closeModalBtn.onclick = function() {
            if (pdfModal) pdfModal.style.display = 'none';
            if (pdfFrame) pdfFrame.src = ''; // Clear iframe src
        }
    }

    window.onclick = function(event) {
        if (event.target == pdfModal) {
            if (pdfModal) pdfModal.style.display = 'none';
            if (pdfFrame) pdfFrame.src = '';
        }
    }

    // --- Dynamic Agenda Item Addition/Removal (for Admin form) ---
    const addAgendaItemBtn = document.getElementById('addAgendaItemBtn');
    const agendaItemsContainer = document.getElementById('agendaItemsContainer');
    
    // Keep track of the next agenda number to display in the form
    // This is for *display* purposes on the form. The actual item_number for DB
    // will be sequential (1, 2, 3...) for a new meeting, or fill gaps if editing.
    let nextFormAgendaDisplayNumber = 1;

    if (agendaItemsContainer) {
        // Initialize nextFormAgendaDisplayNumber based on existing items in container (if any, e.g. on page reload with errors)
        const existingItems = agendaItemsContainer.querySelectorAll('.agenda-item-block');
        if (existingItems.length > 0) {
            // Find the max existing display number
            let maxNum = 0;
            existingItems.forEach(item => {
                const inputNum = item.querySelector('input[name^="agenda_item_number_"]');
                if (inputNum) {
                    const num = parseInt(inputNum.value, 10);
                    if (num > maxNum) maxNum = num;
                }
            });
            nextFormAgendaDisplayNumber = maxNum + 1;
        } else {
             // If no items, and admin wants to add the first one.
             // If the container starts empty, the first item added will be 1.
        }
    }


    if (addAgendaItemBtn) {
        addAgendaItemBtn.addEventListener('click', function() {
            addAgendaItemBlock(nextFormAgendaDisplayNumber);
            nextFormAgendaDisplayNumber = calculateNextDisplayNumber(); // Recalculate after adding
        });
    }

    function addAgendaItemBlock(displayNumber) {
        if (!agendaItemsContainer) return;

        const newItemBlock = document.createElement('div');
        newItemBlock.classList.add('agenda-item-block');
        newItemBlock.dataset.displayNumber = displayNumber; // Store the display number

        // Hidden input to store the display number that JS manages
        const numberInput = document.createElement('input');
        numberInput.type = 'hidden';
        numberInput.name = `agenda_item_number_${displayNumber}`; // Unique name
        numberInput.value = displayNumber;

        const fileLabel = document.createElement('label');
        fileLabel.textContent = `ไฟล์วาระที่ ${displayNumber}:`;
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.name = `agenda_item_file_${displayNumber}`; // Unique name
        fileInput.accept = '.pdf';
        fileInput.required = true; // Make file input required for each agenda block

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = 'ลบวาระนี้';
        removeBtn.classList.add('btn', 'btn-danger', 'btn-sm', 'remove-agenda-item-btn');
        removeBtn.style.marginTop = '10px';

        removeBtn.addEventListener('click', function() {
            newItemBlock.remove();
            renumberAgendaItems(); // Renumber remaining items
            nextFormAgendaDisplayNumber = calculateNextDisplayNumber(); // Recalculate next display number
        });

        newItemBlock.appendChild(numberInput);
        newItemBlock.appendChild(fileLabel);
        newItemBlock.appendChild(document.createElement('br'));
        newItemBlock.appendChild(fileInput);
        newItemBlock.appendChild(document.createElement('br'));
        newItemBlock.appendChild(removeBtn);

        agendaItemsContainer.appendChild(newItemBlock);
    }
    
    function renumberAgendaItems() {
        if (!agendaItemsContainer) return;
        const items = agendaItemsContainer.querySelectorAll('.agenda-item-block');
        let currentDisplayNumber = 1;
        items.forEach(item => {
            // Update the hidden input value and name
            const numberInput = item.querySelector('input[name^="agenda_item_number_"]');
            if (numberInput) {
                numberInput.value = currentDisplayNumber;
                numberInput.name = `agenda_item_number_${currentDisplayNumber}`;
            }

            // Update the label
            const label = item.querySelector('label');
            if (label) {
                label.textContent = `ไฟล์วาระที่ ${currentDisplayNumber}:`;
            }

            // Update the file input name
            const fileInput = item.querySelector('input[type="file"]');
            if (fileInput) {
                fileInput.name = `agenda_item_file_${currentDisplayNumber}`;
            }
            
            item.dataset.displayNumber = currentDisplayNumber; // Update dataset
            currentDisplayNumber++;
        });
    }

    function calculateNextDisplayNumber() {
        if (!agendaItemsContainer) return 1;
        const items = agendaItemsContainer.querySelectorAll('.agenda-item-block');
        if (items.length === 0) {
            return 1;
        }
        // Find the maximum display number currently in the form
        let maxNum = 0;
        items.forEach(item => {
            const num = parseInt(item.dataset.displayNumber, 10);
            if (num > maxNum) {
                maxNum = num;
            }
        });
        return maxNum + 1;
    }


    // --- Confirm Deletion ---
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const confirmed = confirm('คุณแน่ใจหรือไม่ว่าต้องการลบรายการนี้? การกระทำนี้ไม่สามารถย้อนกลับได้');
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    // --- Initialize first agenda item if admin and container is empty ---
    // This ensures there's at least one upload slot when the page loads for admin
    // Only if the container is truly empty (e.g. no server-side validation errors re-populating it)
    const userRoleElement = document.body; // Assuming user_role is available somehow, e.g. data attribute on body
    if (userRoleElement && userRoleElement.dataset.userRole === 'admin' && agendaItemsContainer && agendaItemsContainer.children.length === 0) {
       // console.log("Adding initial agenda block because admin and container is empty.");
       // addAgendaItemBlock(nextFormAgendaDisplayNumber); // Add the first item
       // nextFormAgendaDisplayNumber = calculateNextDisplayNumber();
       // Re-evaluating this: It might be better to let admin click "Add" for the very first one.
       // Otherwise, if they don't want to add any items yet, they have an empty required block.
       // Let's keep it clean and require a click.
    }
     // If there are no agenda items when the page loads (for admin), set the next number to 1.
    if (agendaItemsContainer && agendaItemsContainer.children.length === 0) {
        nextFormAgendaDisplayNumber = 1;
    }


});