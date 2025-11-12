document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('users-table-body');
    const addUserForm = document.getElementById('add-user-form');
    
    // Modal elements
    const modal = document.getElementById('edit-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const editForm = document.getElementById('edit-password-form');
    const modalUsername = document.getElementById('modal-username');
    const modalUserId = document.getElementById('modal-user-id');

    // --- 1. Function to load all users into the table ---
    async function loadUsers() {
        const response = await fetch('/api/admin/users');
        const users = await response.json();
        
        tableBody.innerHTML = ''; // Clear the table
        
        users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.username}</td>
                <td>${user.role}</td>
                <td class="action-buttons">
                    <button class="admin-btn edit-btn" data-id="${user.id}" data-username="${user.username}">Change Password</button>
                    <button class="admin-btn delete-btn" data-id="${user.id}" data-username="${user.username}">Delete</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    // --- 2. Handle Add User Form ---
    addUserForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = addUserForm.username.value;
        const password = addUserForm.password.value;
        const role = addUserForm.role.value;

        const response = await fetch('/api/admin/users/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, role })
        });

        const result = await response.json();
        
        if (response.ok) {
            alert(result.message);
            addUserForm.reset();
            loadUsers();
        } else {
            alert(`Error: ${result.message}`);
        }
    });

    // --- 3. Handle Table Click (Delete & Edit) ---
    tableBody.addEventListener('click', async (e) => {
        const target = e.target;
        
        // --- Handle DELETE ---
        if (target.classList.contains('delete-btn')) {
            const userId = target.dataset.id;
            const username = target.dataset.username;
            
            if (confirm(`Are you sure you want to delete the user "${username}"? This cannot be undone.`)) {
                const response = await fetch('/api/admin/users/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: userId })
                });

                const result = await response.json();
                alert(result.message);
                
                if (response.ok) {
                    loadUsers();
                }
            }
        }
        
        // --- Handle EDIT (Open Modal) ---
        if (target.classList.contains('edit-btn')) {
            modalUserId.value = target.dataset.id;
            modalUsername.innerText = target.dataset.username;
            modal.style.display = 'block';
        }
    });

    // --- 4. Handle Modal (Close & Submit) ---
    function closeModal() {
        modal.style.display = 'none';
        editForm.reset();
    }
    
    closeModalBtn.onclick = closeModal;
    window.onclick = (e) => {
        if (e.target == modal) {
            closeModal();
        }
    };
    
    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const userId = modalUserId.value;
        const newPassword = document.getElementById('new_password').value;
        
        const response = await fetch('/api/admin/users/update-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, password: newPassword })
        });
        
        const result = await response.json();
        alert(result.message);
        
        if (response.ok) {
            closeModal();
        }
    });

    // --- Load users when page opens ---
    loadUsers();
});